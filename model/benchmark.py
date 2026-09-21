"""Small reproducible CPU comparisons, not gas estimates or throughput claims."""

from fractions import Fraction
from statistics import median
from timeit import repeat

from .examples import change, commit
from .ledger import Batch, Ledger, approve
from .payoffs import Knot, Payoff
from .table import Atom, OutcomeTable


def micros(function, iterations=20):
    return median(repeat(function, repeat=5, number=iterations)) * 1_000_000 / iterations


def representation_benchmarks():
    atoms = [Atom("ramp", 100, 95, 105, 0)]
    compact = Payoff.ramp(95, 105, 100, void=0)
    local_table = OutcomeTable.from_atoms(atoms)
    compact_time = micros(compact.extrema)
    local_time = micros(local_table.extrema)
    shared_rows = []
    for boundary_count in (10, 100, 1000, 5000):
        # Exactly boundary_count unique boundaries, including the profile's two.
        axis = [95, 105] + [Fraction(-i - 1) for i in range(boundary_count - 2)]
        shared = OutcomeTable.from_atoms(atoms, extra_boundaries=axis)
        if shared.extrema() != compact.extrema() or local_table.extrema() != compact.extrema():
            raise AssertionError("benchmark profiles are not equivalent")
        shared_rows.append({"shared_boundaries": len(shared.boundaries),
                            "compact_boundaries": len(compact.knots),
                            "compact_scalar_slots": 2 + 3 * len(compact.knots),
                            "shared_scalar_slots": len(shared.boundaries) + shared.stored_values,
                            "local_table_scalar_slots": len(local_table.boundaries) + local_table.stored_values,
                            "compact_min_us": compact_time, "local_table_min_us": local_time,
                            "shared_table_min_us": micros(shared.extrema)})
    growth_rows = []
    for boundary_count in (2, 10, 100, 1000):
        # Alternating steps: bounded 0/1 exposure with genuinely distinct knots.
        knots = tuple(Knot(i, 1 if i % 2 == 0 else -1) for i in range(boundary_count))
        compact = Payoff(0, knots, 0)
        # Build this comparator directly from the stated 0/1 alternating pattern.
        values = [Fraction(0)] + [Fraction(1 if i % 2 == 0 else 0)
                                 for i in range(boundary_count)]
        local_table = OutcomeTable(tuple(Fraction(i) for i in range(boundary_count)),
                                   tuple((v, v) for v in values), Fraction(0))
        if compact.extrema() != local_table.extrema():
            raise AssertionError("growth benchmark extrema differ")
        growth_rows.append({"account_boundaries": boundary_count,
                            "compact_min_us": micros(compact.extrema),
                            "local_table_min_us": micros(local_table.extrema),
                            "compact_normalize_us": micros(lambda: Payoff(0, knots, 0))})
    return shared_rows, growth_rows


def unrelated_account_benchmarks():
    """Actual unrelated funded claims; full global audit stays outside timing."""
    rows = []
    for unrelated in (0, 10, 100, 1000):
        book = Ledger()
        for name in ("alice", "bob", "backer"):
            book.register(name, 1_000_000)
        for index in range(unrelated):
            name = f"unrelated-{index}"
            book.register(name, 0)
            payout = Payoff.step(index, 1, void=0)
            # The backer is outside the timed trade; its complex profile is not scanned.
            commit(book, change(book, "backer", -payout, cash=1), change(book, name, payout))
        book.audit()
        samples = []
        for _ in range(5):
            # Alternate a fully funded claim between two fresh trading accounts.
            # Time only execute; preparing harness approvals is measured nowhere.
            from time import perf_counter
            elapsed = 0
            payout = Payoff.interval(-2, -1, 1, void=0)
            for index in range(20):
                opening = index % 2 == 0
                delta = payout if opening else -payout
                flow = 1 if opening else -1
                batch = Batch(book.market_id, 100,
                              (change(book, "alice", delta, cash=flow),
                               change(book, "bob", -delta, cash=flow)))
                approvals = [approve(batch, c.account) for c in batch.changes]
                start = perf_counter()
                book.execute(batch, approvals)
                elapsed += perf_counter() - start
            samples.append(elapsed * 1_000_000 / 20)
        book.audit()
        rows.append({"unrelated_funded_accounts": unrelated, "execute_us": median(samples)})
    return rows
