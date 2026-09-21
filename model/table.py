"""Independent explicit-interval reference, constructed from elementary atoms.

It uses direct elementary formulas, not Payoff.value() or its coefficient sweep.
"""

from bisect import bisect_right
from dataclasses import dataclass
from fractions import Fraction

from .payoffs import VOID, q


@dataclass(frozen=True)
class Atom:
    kind: str
    amount: Fraction
    lower: Fraction = Fraction(0)
    upper: Fraction = Fraction(0)
    void: Fraction = Fraction(0)

    def __post_init__(self):
        for field in ("amount", "lower", "upper", "void"):
            object.__setattr__(self, field, q(getattr(self, field)))
        if self.kind not in {"constant", "step", "below", "interval", "ramp"}:
            raise ValueError("unknown atom")
        if self.kind in {"interval", "ramp"} and self.lower >= self.upper:
            raise ValueError("invalid boundaries")
        if self.kind == "constant" and self.void != self.amount:
            raise ValueError("a cash constant must agree in VOID")

    @property
    def boundaries(self):
        if self.kind == "constant":
            return ()
        if self.kind in {"interval", "ramp"}:
            return self.lower, self.upper
        return (self.lower,)

    def value(self, x, *, left=False):
        if x == VOID:
            return self.void
        x = q(x)
        if self.kind == "constant":
            return self.amount
        above_lower = x > self.lower if left else x >= self.lower
        if self.kind == "step":
            return self.amount if above_lower else Fraction(0)
        if self.kind == "below":
            return Fraction(0) if above_lower else self.amount
        if self.kind == "interval":
            below_upper = x <= self.upper if left else x < self.upper
            return self.amount if above_lower and below_upper else Fraction(0)
        fraction = min(Fraction(1), max(Fraction(0),
                       (x - self.lower) / (self.upper - self.lower)))
        return self.amount * fraction


@dataclass(frozen=True)
class OutcomeTable:
    boundaries: tuple[Fraction, ...]
    # For every open interval: start value and end limit. Boundaries belong right.
    cells: tuple[tuple[Fraction, Fraction], ...]
    void: Fraction

    @classmethod
    def from_atoms(cls, atoms, *, extra_boundaries=()):
        atoms = tuple(atoms)
        boundaries = tuple(sorted({q(x) for x in extra_boundaries} |
                                  {x for atom in atoms for x in atom.boundaries}))

        def evaluate(x, left=False):
            return sum((a.value(x, left=left) for a in atoms), Fraction(0))

        if not boundaries:
            value = evaluate(0)
            return cls((), ((value, value),), evaluate(VOID))
        first = evaluate(boundaries[0], left=True)
        cells = [(first, first)]
        for lo, hi in zip(boundaries, boundaries[1:]):
            cells.append((evaluate(lo), evaluate(hi, left=True)))
        last = evaluate(boundaries[-1])
        cells.append((last, last))
        return cls(boundaries, tuple(cells), evaluate(VOID))

    def value(self, result):
        if result == VOID:
            return self.void
        x = q(result)
        index = bisect_right(self.boundaries, x)
        start, end = self.cells[index]
        if index == 0 or index == len(self.boundaries):
            return start
        lo, hi = self.boundaries[index - 1], self.boundaries[index]
        return start + (end - start) * (x - lo) / (hi - lo)

    def extrema(self):
        values = (v for cell in self.cells for v in cell)
        low = high = self.void
        for value in values:
            low, high = min(low, value), max(high, value)
        return low, high

    @property
    def stored_values(self):
        return 2 * len(self.cells) + 1
