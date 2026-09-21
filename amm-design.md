# A backstop automated maker

Status: rough model, not a committed component. No implementation, no measurements,
no parameter calibration. This document works out whether a cost-function maker can
sit inside the account ledger without weakening its guarantees, and what it would
cost to run.

Scope decision: **this is a fallback, not the primary liquidity source.** Quoting is
expected to come from independent makers through the order and package mechanisms in
[quote-workflow.md](quote-workflow.md). The role described here is narrower: guarantee
that *some* executable price always exists, particularly for exits. It is a floor
under liquidity, not a market.

See [core-design.md](core-design.md) for the ledger this must obey.

---

## 1. Why a backstop is worth specifying at all

Two gaps in the current design have no other answer.

**Exit liquidity.** A participant whose counterparty has stopped quoting can be unable
to leave a position before expiry. Their payout is still fully funded, so this is a
liquidity limitation rather than a solvency one, but it is the limitation most likely
to be felt.

**Whole-account exits.** Section 7 of the core design shows that closing a netted
position one leg at a time can require far more capital than closing it as a package,
and can exceed the original worst-case commitment. That analysis assumes a
counterparty willing to price the complete package. A maker that will quote any
bounded profile, including an account's entire remaining payout, is the mechanism that
makes the whole-position exit available rather than theoretical.

A backstop is a weaker claim than a market. It says a price exists, not that the price
is good.

---

## 2. The construction

Let `X` be the market's permitted numeric outcome range, quantized to the settlement
lattice, with `n` ticks. Let `mu` be a fixed base measure on `X` with total mass 1 and
a floor `mu({x}) >= eps` at every tick.

Let `q(x)` be the total payout the maker has sold, as a function of outcome — held in
the same compact coefficient form as any other account profile.

Define the cost functional:

```
C(q) = b * log( integral over X of exp(q(x)/b) dmu(x) )
```

`b > 0` is the depth parameter. The price charged for selling an additional bounded
profile `D(x)` is:

```
price(D) = C(q + D) - C(q)
```

Selling a constant payout `c` at every outcome costs exactly `c`, which is the property
that makes this consistent with an account ledger holding cash.

The implied distribution used for pricing is the gradient:

```
p(x) = exp(q(x)/b) * mu(x) / integral of exp(q/b) dmu
```

This is the maker's current view. It is not an assertion that the view is correct.

The gradient is the implied distribution described in section 1 of [core-design.md](core-design.md): pricing a claim over a set of states returns that set's implied probability mass, with no differentiation or curve fitting in between. For a backstop maker this is a derived quantity of its own prior and its own flow, so it carries no more information than the flow it has seen. It becomes a market distribution only when independent makers are quoting against it.

---

## 3. Why it fits the ledger

The maker is an ordinary account, subject to the same two invariants. It deposits a
fixed amount `M` once and never requires a top-up.

Let the maker start with `W_amm = M` and trade only at cost-function prices. After
selling total profile `q` and collecting total premium `C(q) - C(0)`, its profile is:

```
W_amm(x) = M - q(x) + C(q)          with C(0) = 0 since mu has mass 1
```

Bound the worst case. For any tick `x`:

```
C(q) = b log( integral exp(q/b) dmu ) >= b log( exp(q(x)/b) * mu({x}) )
     = q(x) + b log mu({x})
     >= q(x) + b log eps
```

Therefore `q(x) - C(q) <= -b log eps = b log(1/eps)` at every tick, and:

```
inf_x W_amm(x) >= M - b log(1/eps)
```

So setting

```
M = b * log(1/eps)
```

makes `inf W_amm >= 0` hold permanently, for any sequence of trades, without a single
additional deposit.

**The funding check never fails for a maker trade.** The maker's maximum loss is known
before it quotes anything, and it is posted in full at the start. It cannot break the
jar and it cannot be asked for more money. That is the property that lets it sit
inside this design rather than beside it.

The engine still runs its ordinary checks. Nothing here asks for an exemption.

---

## 4. Computing the price

The integral has a closed form when both `q` and the base measure are piecewise over
the same breakpoints.

`q` is piecewise linear with `k` breakpoints and constant tails. Give `mu` a piecewise
constant density `m_i` on each segment. On segment `[k_i, k_{i+1}]` where
`q(x) = a_i * x + c_i`:

```
integral of exp(q/b) dmu over the segment
    = m_i * (b/a_i) * [ exp((a_i * k_{i+1} + c_i)/b) - exp((a_i * k_i + c_i)/b) ]     if a_i != 0
    = m_i * (k_{i+1} - k_i) * exp(c_i/b)                                              if a_i == 0
```

Summing over segments gives `C(q)` in `O(k)` — in the number of the maker's own
breakpoints, **not** in the number of ticks. Pricing a trade `D` with `k_D`
breakpoints costs `O(k + k_D)`.

This is the reason the construction is worth considering at all: the pricing layer
consumes exactly the representation the ledger already stores, and an arbitrary custom
profile is no harder to price than a simple one.

Implementation notes that are not optional:

- Factor out `max(q)/b` before exponentiating. Direct evaluation overflows quickly.
- `a_i` near zero is numerically unstable in the first branch; switch to a series
  expansion below a threshold rather than to the `a_i == 0` branch.
- Prices are computed in floating point, then **rounded against the maker** to the
  settlement lattice before the batch is built. The ledger's exact arithmetic starts
  at the rounded value. Pricing precision and settlement precision are separate
  concerns and must not share a code path.

---

## 5. Parameters

| Parameter | Meaning | Effect of increasing |
|---|---|---|
| `b` | Depth | Tighter prices, less impact per unit traded, larger `M`, larger worst-case loss |
| `eps` | Base-measure floor per tick | Smaller `M`, but the maker will quote extreme outcomes badly |
| `mu` | Prior shape | Where the maker starts before any flow arrives |
| `f` | Fee or spread applied around the gradient price | Revenue, offset against adverse selection |

Approximate price impact of a trade of size `s` is `s/b`, so `b` is the only real
depth control.

For a backstop role, `b` should be **small**. Wide quotes, modest capital, always
present. A small `b` makes the maker a poor competitor to a real maker quoting
tightly, which is the intended outcome — it should be the price of last resort, not
the price of first resort.

Every parameter above is unvalidated. No calibration work has been done.

---

## 6. Fees and adverse selection

The gradient price carries zero spread. Without a fee the maker is a pure
loss-absorber, and `M` is a budget that gets spent.

Revenue comes from a fee `f` applied around the gradient price. Whether that revenue
exceeds losses depends entirely on the ratio of uninformed to informed flow, which
cannot be estimated from this design.

Two points worth stating plainly:

- **The flexible payout vocabulary is an advantage for informed traders.** A binary
  market lets an informed participant express one disagreement. An arbitrary bounded
  profile lets them build an exposure concentrated exactly where the maker's `mu` is
  most wrong and nowhere else. This is inherent to expressiveness and is not fixable;
  it is a reason to price unusual shapes more widely than common ones.
- **Whoever funds `M` bears this.** If the protocol funds it, the protocol carries
  trading risk and should say so. If third-party providers fund it, they are taking a
  position whose expected return is unknown and must not be described as yield. This
  is a genuine allocation decision, not an implementation detail, and it is the main
  reason to keep the component optional.

The loss is bounded at `M` per market. That bound is the one thing this construction
guarantees.

---

## 7. How it coexists with maker quotes

The order and package mechanisms stay primary. The backstop publishes derived quotes
at its configured spread, and a taker receives whichever source is better for the
complete requested change.

The backstop's distinguishing capability is that it will price **any** bounded profile,
including an entire account's remaining payout, which a fixed order book cannot
express. That makes it the natural provider for the whole-position exit in section 7
of the core design, and for the proportional-unwind operation, even when it is
uncompetitive on ordinary directional flow.

It does not change what authorization, funding, conservation or atomicity mean. It is
an account, and it authorizes its own changes like any other.

---

## 8. What this does not establish

- No implementation, no tests, no benchmarks. The complexity claims in section 4 are
  derivations, not measurements.
- No calibration of `b`, `eps`, `mu` or `f`, and no estimate of expected loss.
- No evidence that a backstop is sufficient to make markets usable, or that
  independent makers will quote alongside it.
- No fixed-point pricing design. Section 4 assumes floating-point pricing feeding a
  lattice-rounded batch, and that boundary has not been specified.
- No treatment of quote validity, reservation, or concurrent state change. Those are
  open questions in the core design and this component does not resolve them.
- Bounded maximum loss is a statement about the accounting, not about whether the
  capital is well spent.

## 9. The next decision

The question to answer before building anything is narrow: **does an executable price
always existing change what a participant can do, in a way that independent makers
would not already provide?**

The whole-position exit is the strongest candidate, because it is the case where a
missing counterparty demonstrably costs a participant more than their original
worst-case commitment. If that case can be served by a package quote from an ordinary
maker, this component is unnecessary and should not be built.
