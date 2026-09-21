"""Bounded, right-continuous piecewise-affine payouts with an explicit VOID state."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

VOID = "VOID"


def q(value: int | str | Fraction) -> Fraction:
    """Do not silently import binary floats into financial arithmetic."""
    if isinstance(value, bool) or not isinstance(value, (int, str, Fraction)):
        raise TypeError("use an integer, decimal/rational string, or Fraction")
    return Fraction(value)


@dataclass(frozen=True)
class Knot:
    x: Fraction
    jump: Fraction = Fraction(0)
    slope_change: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        for field in ("x", "jump", "slope_change"):
            object.__setattr__(self, field, q(getattr(self, field)))


@dataclass(frozen=True)
class Payoff:
    base: Fraction = Fraction(0)
    knots: tuple[Knot, ...] = ()
    void: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "base", q(self.base))
        object.__setattr__(self, "void", q(self.void))
        combined: dict[Fraction, tuple[Fraction, Fraction]] = {}
        for knot in self.knots:
            if not isinstance(knot, Knot):
                raise TypeError("knots must be Knot instances")
            jump, slope = combined.get(knot.x, (Fraction(0), Fraction(0)))
            combined[knot.x] = jump + knot.jump, slope + knot.slope_change
        canonical = tuple(
            Knot(x, jump, slope)
            for x, (jump, slope) in sorted(combined.items())
            if jump or slope
        )
        if sum((k.slope_change for k in canonical), Fraction(0)) != 0:
            raise ValueError("unbounded tail: slope changes must sum to zero")
        object.__setattr__(self, "knots", canonical)

    @classmethod
    def constant(cls, amount: int | str | Fraction) -> Payoff:
        amount = q(amount)
        return cls(amount, (), amount)

    @classmethod
    def step(cls, level, amount, *, void) -> Payoff:
        return cls(0, (Knot(level, amount),), void)

    @classmethod
    def below(cls, level, amount, *, void) -> Payoff:
        amount = q(amount)
        return cls(amount, (Knot(level, -amount),), void)

    @classmethod
    def interval(cls, lower, upper, amount, *, void) -> Payoff:
        lower, upper, amount = q(lower), q(upper), q(amount)
        if lower >= upper:
            raise ValueError("interval requires lower < upper")
        return cls(0, (Knot(lower, amount), Knot(upper, -amount)), void)

    @classmethod
    def ramp(cls, lower, upper, amount, *, void) -> Payoff:
        lower, upper, amount = q(lower), q(upper), q(amount)
        if lower >= upper:
            raise ValueError("ramp requires lower < upper")
        slope = amount / (upper - lower)
        return cls(0, (Knot(lower, 0, slope), Knot(upper, 0, -slope)), void)

    def __add__(self, other: Payoff) -> Payoff:
        if not isinstance(other, Payoff):
            return NotImplemented
        return Payoff(self.base + other.base, self.knots + other.knots,
                      self.void + other.void)

    def __neg__(self) -> Payoff:
        return self * -1

    def __sub__(self, other: Payoff) -> Payoff:
        return self + (-other)

    def __mul__(self, amount) -> Payoff:
        amount = q(amount)
        return Payoff(self.base * amount,
                      tuple(Knot(k.x, k.jump * amount, k.slope_change * amount)
                            for k in self.knots), self.void * amount)

    __rmul__ = __mul__

    def value(self, result, *, left_limit: bool = False) -> Fraction:
        if result == VOID:
            return self.void
        x = q(result)
        value = self.base
        for knot in self.knots:
            if knot.x > x:
                break
            if knot.x < x or not left_limit:
                value += knot.jump
            value += knot.slope_change * (x - knot.x)
        return value

    def extrema(self) -> tuple[Fraction, Fraction]:
        """Exact infimum and supremum, including both sides of jumps and VOID."""
        low, high = min(self.base, self.void), max(self.base, self.void)
        value, slope, previous = self.base, Fraction(0), None
        for knot in self.knots:
            if previous is not None:
                value += slope * (knot.x - previous)
            low, high = min(low, value), max(high, value)
            value += knot.jump
            low, high = min(low, value), max(high, value)
            slope += knot.slope_change
            previous = knot.x
        return low, high

    @property
    def minimum(self) -> Fraction:
        return self.extrema()[0]

    @property
    def is_zero(self) -> bool:
        return self.base == 0 and not self.knots and self.void == 0

    @property
    def endpoint_checks(self) -> int:
        return 2 + 2 * len(self.knots)

    def encoded(self) -> dict:
        return {"base": str(self.base), "void": str(self.void),
                "knots": [[str(k.x), str(k.jump), str(k.slope_change)]
                          for k in self.knots]}


def total(profiles: Iterable[Payoff]) -> Payoff:
    base, void, knots = Fraction(0), Fraction(0), []
    for profile in profiles:
        base += profile.base
        void += profile.void
        knots.extend(profile.knots)
    return Payoff(base, tuple(knots), void)
