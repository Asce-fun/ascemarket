# AsceMarket in plain words

A simple explanation of what we have built so far, and the five changes worth making.
No maths. Small numbers. Real ones from our own documents.

Companion to [ps.md](ps.md), [core-design.md](core-design.md) and [quote-workflow.md](quote-workflow.md).

---

# Part 1 — What we have right now

## The jar

Picture a big glass jar.

Everybody who wants to trade puts money in the jar. Nobody's money is "theirs" any
more — instead, each person holds a **slip of paper**.

The slip says: *"Here is how much you get back, for every possible thing that could
happen."*

A slip might say:

> If ETH ends below $2,800 → you get $100
> If ETH ends above $2,800 → you get $0

That's it. That's the whole product. People trade slips, and the jar holds the money.

## What we're actually selling

Most places sell you a **thing**: a share, a contract, a bet. We sell something one step
more basic — **money in particular futures.**

Think of every possible ending as a separate box. ETH ends at 2,600 — that's a box.
ETH ends at 3,400 — a different box. Your slip just says how much money is waiting for
you in each box.

That sounds like a small difference. It isn't. Three things fall out of it for free:

**1. Things cancel out on their own.** If two slips are about the same future, they're
both just "money in boxes," and money in boxes adds up. We never need a rule saying
*"these two particular products cancel."* Put "A wins" and "A or B wins" together and
the engine simply sees what's left — the same way it handles a high tail and a low
tail. Somewhere selling *things* has to be told, product by product, which ones relate.
We can't miss one.

**2. You can ask for any shape.** Since we're handing out money box by box, you're not
picking from a menu. If your real exposure is a weird staircase, you can have the weird
staircase.

**3. The prices tell you the odds.** If a slip that pays $1 when ETH ends between 2,900
and 3,000 costs 12 cents, the market is telling you there's roughly a 12% chance of
that. Read it straight off the price.

That third one is worth pausing on. A normal prediction market gives you **one number**
— *"62% chance of a rate cut."* Ours gives you the **whole picture**: how likely every
level is, all at once. Options markets technically contain that too, but you have to
dig it out with maths. Here you just read it.

*The honest catch:* those odds are only as good as the trading behind them. A quiet
market gives you a very confident-looking answer made of nothing. Real prices or don't
publish.

**And the real limit:** one market covers one question. All of this works beautifully
*within* "where does ETH end on Friday." It doesn't stretch across "ETH on Friday **and**
who wins the election." We cover one slice of the future at a time, not the future.

## The two rules

Everything we have built exists to enforce two rules.

**Rule 1 — No slip can ever promise a negative number.**
You can never end up owing money. The worst thing that can happen is your slip pays
you nothing.

**Rule 2 — Add up everyone's slips, and it must exactly equal what's in the jar.**
For *every* possible ending. Not on average. Not usually. Every single one.

If a trade would break either rule, the trade is refused. Nothing happens. The jar is
untouched.

## The clever bit: two promises that can't both come true

Here's the thing that makes our system worth building.

Say a seller makes two promises:

- "I'll pay you $100 if ETH ends **below** $2,800"
- "I'll pay you $100 if ETH ends **above** $3,200"

A normal system looks at these and says: *two promises of $100, so lock up $200.*

But ETH can't finish below $2,800 **and** above $3,200. Only one of those can happen.
So the seller can only ever owe $100 — never $200.

Our system sees that. It asks for $100, not $200.

In our worked example this takes the seller's real cash from **$146 down to $46**.
Same promises. Same safety. A third of the money.

We call this *netting*. It is the heart of the whole design.

## Wait — where does the $100 actually come from?

This is the bit that trips everyone up, so let's be very concrete.

**The seller is not promising $100 while only putting in $46.** The jar really does
hold the whole $100. Here's who put it there:

| Who | Puts in |
|---|---:|
| Buyer of the "below $2,800" slip | $22 |
| Buyer of the "above $3,200" slip | $32 |
| **Seller tops up the rest** | **$46** |
| **Total in the jar** | **$100** |

The most anyone can ever be owed is $100. The jar has $100. Every promise is fully
paid for, today, in cash.

The seller's $46 is not "the collateral for a $100 promise." It's just **the gap**
between what the buyers already paid ($54) and the biggest cheque the jar might ever
have to write ($100).

Now do it the other way. If those two promises *could* both pay, the jar would need
**$200**. The buyers still only paid $54. So the seller would have to top up
$200 − $54 = **$146**.

> So the entire netting result is one question: **how big does the jar need to be?**
> $200, or $100? Everything else is identical.

That's the whole trick. There is no leverage, no borrowing, and nothing on credit.

## Why nobody gets liquidated

This is the part most people miss, and it is our best feature.

Other trading venues let you put down a small deposit — Rates Exchange asks for about
0.3% — and borrow the rest. That's cheap. But if the price moves against you, they
**take your position away** to protect everyone else. That's a liquidation.

We don't do that. We make you put in the full worst-case amount up front. Boring,
expensive, and it means:

- Nobody can ever be liquidated
- Nobody's payout ever gets cut short because someone else blew up
- There is no "sorry, the pool ran dry"

If you bought protection, you get paid. Full stop. That is the promise, and we have
actually proved it in the model.

## Can I take my slip somewhere else?

Not today, and this is a genuine weakness worth being upfront about.

On Polymarket your position is a **token**. You can move it, lend against it, use it in
another app. Our slips are entries in our own ledger. They don't travel.

Why not? Because our cheap collateral comes from looking at your **whole** account at
once. Your $46 is low precisely because your two promises cancel. Rip one promise out
and hand it to someone else, and the cancelling stops — so the discount can't go with it.

> **The netting belongs to the account, not to the position.**

Two ways out, neither built yet:

- **Move the whole slip.** Hand over your entire position in one piece and every
  cancellation inside it survives, because nothing got separated. This is also the
  clean version of the "sell my whole position" button from Part 2 — it's the same
  operation.
- **Break it into standard pieces.** Our shapes split into simple building blocks that
  always come in pairs adding up to $1 — put in $1, get both halves; hand both back,
  get your $1. Those halves are identical between people, so they can be traded.

The second one costs you money. Pull a position out on its own and it has to be fully
backed on its own — you might need $200 of backing outside for something that cost $100
inside. **That gap is exactly the netting you left at home.** It's not a bug, it's the
honest price of taking things apart, and we should show that number rather than bury it.

## What we've built vs. what we haven't

**Built and tested:** the jar, the slips, the two rules, the netting, the ability to
change several slips at once in a single all-or-nothing move. 28 tests pass.

**Not built:** anything a real person could use. No prices. No sellers. No wallets.
No signatures. No real money. It's a very well-behaved calculator.

That's fine — we're in design phase. But it means the open questions are design
questions, not code questions.

---

# Part 2 — Buying and selling before the end

*"When I buy a share I can just sell it higher. Isn't that how Polymarket works? So
how can $46 possibly be enough?"*

Good question. The answer is that **buyers and sellers are completely different
animals**, and the $46 is a *seller* number.

## Buyers have it easy

| | Buyer | Seller |
|---|---|---|
| What they pay up front | The price — $22 | Tops up the jar — $46 |
| Worst thing that can happen | They lose exactly what they paid | They lose their top-up |
| Collateral ever needed | **None. Ever.** | Yes |
| Can they sell early? | Yes — just like a share | Yes, but it's a whole new trade |

A buyer pays $22 and that is *already* their maximum loss — they handed it over on day
one. There is nothing left to collateralise. They can sell whenever they like, at
whatever price someone will pay, exactly like a share.

**This is exactly the Polymarket experience.** You buy at 22c, it goes to 90c, you
sell. Easy. Nothing about our design changes that.

(Polymarket even has a small version of our netting — the "negative risk adapter" we
cite in `ps.md`. It lets you net mutually exclusive outcomes *inside one
multi-outcome market*. Our claim is doing it for any numeric shape, across a whole
account.)

## So what happens when a buyer sells at a profit?

ETH crashes to $2,600. The "below $2,800" slip is now worth ~$90. The buyer paid $22.
They want their profit. **Who do they sell to?**

**Case A — they sell to somebody else.** The slip changes hands for $90. The buyer
banks $68 of profit and walks away.

What happens to the seller? **Absolutely nothing.** They still owe $100 if ETH ends
below $2,800 — just to a new person now. Their $46 is untouched. The jar doesn't even
notice.

> This is the normal case. This is what happens on Polymarket every day. The original
> seller is never involved and never needs another cent.

**Case B — they sell back to the original seller.** Now the seller is spending real
money to cancel their own obligation. This one is different, and it's where it gets
dangerous.

## The trap: the seller closing out leg by leg

Watch what happens if the seller tries to exit one piece at a time.

**Month 1 — ETH at $2,600.** The "below" slip is worth ~$90. The seller buys it back
for $90.

Their slip becomes `$10 − H`. If ETH later ends above $3,200 that's **−$90** — a
negative slip, which breaks Rule 1. So the engine demands a **$90 deposit** before it
will allow the trade. The seller is now $136 in.

**Month 2 — ETH rallies to $3,400.** Now the *other* slip is worth ~$90. They buy
that back too, and are left with a flat $10 which they withdraw.

**Put in $136. Got back $10. Lost $126.** They were told their worst case was $46.

## Is netting broken, then?

No. And this is the sentence to remember:

> **The two slips can never both *pay out*. But they can both become *expensive* —
> just not at the same moment.**

At the end, only one tail can happen. That's a fact, and $46 is real. What breaks it
is **time**: the "below" slip was expensive in month 1, the "above" slip was expensive
in month 2. A seller who exits at two different moments pays the high price twice.

Netting protects you **at the finish line**. It does not protect you from your own
trading decisions along the way.

Two things stayed true the entire time:

- **The jar never broke.** Every slip stayed non-negative at every step.
- **Nobody forced the seller into it.** If they hadn't had the $90, the trade would
  simply be **refused** and they'd still be sitting on the original position with its
  $46 cap intact. That's the difference from a normal venue, where a bad price move
  takes your position away whether you like it or not. Here a price move does nothing
  at all unless *you* choose to act.

## The fix

The $126 was not caused by the maths. It was caused by **exiting one leg at a time.**

At ETH $2,600, the seller's *whole remaining position* is worth about **$10**. If they
could sell the entire thing in one move: put in $46, get back $10, **lose $36.**

$36 instead of $126. And here's the part that matters:

> **Selling the whole position at once can never lose more than the original $46.**
> Worst case it's worth $0 and you lose exactly your $46. The promise holds.

Leg-by-leg exit blows straight through the cap. Whole-position exit respects it.

Three things this tells us to build:

1. **"Sell my whole position" must be a real button**, not something cobbled together
   from separate legs. This is the strongest argument for the robot seller in Change 2
   — we need something that will quote an *entire account*, not just one shape.
2. **Proportional unwind** — "reduce everything by 40%." Shrink the whole slip and its
   worst case shrinks with it, so it is *always* funded and *never* needs new money.
   This should be the default exit.
3. **Show all three prices side by side** at exit time: close this leg alone → *add
   $90*; close both → *$X*; sell the whole position → *receive $10*. A user who only
   sees the first number will make the $126 mistake.

This is the single biggest way our product could surprise someone badly. It's an
execution-design problem, not a flaw in the accounting.

---

# Part 3 — The problem nobody has named yet

Our documents talk a lot about locking up less money. But the real question is
different, and we should say it out loud.

**Who wants to be the seller?**

A seller locks $46 for three months. At the end they get it back plus whatever they
earned. If they want a decent return on that money, they have to charge a fat price.
Fat prices mean nobody wants to buy.

So the chain is:

> money locked up → how much the seller must charge → whether anyone trades

And here's the part that reframes everything: our netting doesn't really make life
cheaper for the *buyer*. It makes the **seller's return three times better** for the
same price charged. That means the seller can charge less. *That* is how netting
reaches the customer — through cheaper prices, not through a smaller deposit.

We should be selling this to sellers, not buyers.



---

# Part 4 — The five changes

## Change 1 — Let the number be anything, not just "the price at 3pm" ----agree with this make the respective changes in the docs

**Now:** the thing we settle on has to be a price at one moment. "What is ETH worth
on Friday at 8am?"

**Change:** let it be *any* single number you can measure and agree on beforehand.

- The **average** price over a month
- The **average interest rate** over three months
- How **bumpy** the price was
- Average price of GPU compute
- How much it rained

**Why it works:** our jar doesn't care where the number came from. It only cares
that there is *one* final number, and that everyone agreed in advance how to measure
it. Nothing inside the engine changes. Not one line.

**Why it matters:** this alone turns us from "a market on ETH's Friday price" into
"a market on interest rates, on volatility, on compute costs." Interest rate
products are exactly what Rates Exchange sells — and we'd be selling them without
liquidations.

One catch: our slips must have a floor and a ceiling. So we can do a *capped*
interest rate deal, not an unlimited one. That's fine — a fully-funded product has
to be capped anyway.

**This is the cheapest and biggest change on the list.**

## Change 2 — Build a robot seller ---this should not be our primary concern but porobably a fallback method less on propeoroy ---give me a seprate mf dile for the rough AMM model design 

**Now:** we've said "pricing is somebody else's problem." Which quietly means: we
have no sellers, and a market with no sellers isn't a market.

**Change:** build an automatic seller that will quote a price on any shape, instantly.

**Why it works:** there's a well-known recipe for this (we already cite the papers).
The nice surprise is that the maths lines up with what we already store. Our slips
are made of straight lines. The robot's price formula, applied to straight lines,
works out to a plain formula you can compute directly — no guessing, no simulation.
Fast, exact, and it uses the same data we already keep.

Better still: the robot has a **known maximum loss**. We can work out that number in
advance, drop it in the jar, and the robot becomes just another slip-holder obeying
the same two rules. It can never break the jar.

**Why it matters:** this is the difference between a design document and a market.

## Change 3 — Show every seller their "worst day"

**Now:** we tell a seller "lock up $46" and don't explain where that came from.

**Change:** show them.

Every seller has exactly **one worst day** — one future price where they lose the
most. That single day is what sets their $46. Nothing else matters.

Now here's the useful part. If somebody offers them a new trade that pays out
**nowhere near** their worst day, that trade needs **no extra money at all**. It's
free to take.

**Why it matters:** sellers will hunt for those trades. They'll quote cheaper prices
for the trades that don't cost them anything, and pricier ones for trades that pile
onto their bad day. The market gets smarter on its own. This costs us almost nothing
to build — we already calculate the worst day. We just never show it to anyone.

## Change 4 — Two free ways to make the money cheaper ----- User holding the psoition till maturity should earn yiedld that way will incentise Hedgers ...but this should be a seprate priority because if the collateral will be invested into third aprty protocol then it will be not good ....we may can give some part of protocol fees back to the jar.

**4a. Let the jar earn interest.**

Right now all that money sits doing nothing. Put it somewhere safe that pays
interest, and hand the interest back to people based on how much each one put in.

It slots straight into our existing rules — giving someone extra money is a move we
already support and already tested.

*Honest catch:* wherever we park that money is a new thing that could go wrong. Our
whole pitch is "your payout is guaranteed." We'd be adding a small crack in that. It
might still be worth it. It's a judgement call, not a free win.

**4b. Let guaranteed money work twice.**

If your slip says *"you get at least $10, whatever happens"* — that $10 is already
yours. It's not a maybe.

So let it back a trade in a **different** market. Not a guess about how the two
markets move together — an actual, locked-in $10 that exists no matter what.

**Why it matters:** this fixes the rollover problem. Today, when your three-month
protection is ending and you want the next three months, you have to fund both at
once. With this, the guaranteed part of the old one pays for the new one.

**A warning:** do *not* extend this to "these two markets usually move together, so
we'll ask for less." That's a guess, and guesses are exactly what causes
liquidations. Our whole value is that we never guess. Only ever use the truly
guaranteed floor.

## Change 5 — Decide the money rounding now, before it bites- --- this is not an issue we will handle it exactly how polymarket does it .

**Now:** our slips can pay out half a cent. Real money doesn't have half cents. We've
written this down as "unresolved."

**Change:** make a rule today that every slip must pay a **whole number of cents**, at
every price we allow. Two parts:

- Prices move in fixed steps (like $0.01, not any number)
- Slip shapes can only slope at rates that land on whole cents

**Why it matters:** if you round a payout down, someone gets shortchanged. If you
round up, the jar comes up short — and now we've broken Rule 2, which is the entire
foundation. Rounding a few slips separately and then adding them up can quietly
change what the contract actually said.

This is a one-paragraph rule right now. After we've shipped a shape language and
people hold real slips, it's a rewrite. **Do it now.**

Bonus: Change 2 (the robot) needs price steps anyway. These two fit together.

---

# Part 5 — Things to stop worrying about

**How we store the shapes.** We have three pages of speed tests comparing storage
formats. At the sizes we actually care about, the difference is invisible. Our own
document already says "keep the simple one." Let's listen to it.

**A nicer editor.** Being easy to use is expected, not special. We've correctly
talked ourselves out of this twice already.

**Markets on two things at once** ("ETH price *and* the weather"). The maths still
works but the number of cases explodes. Not now.

---

# Part 6 — The short version

We sell money in particular futures. Every possible ending is a box, your slip says
what's waiting in each box, and the jar holds enough to pay every box. Because that's
the unit, related positions cancel on their own, any shape is expressible, and the
prices double as the odds.

The jar can never run dry and slips can never go negative. It's genuinely safe in a way
that cheaper venues are not. Nobody gets liquidated. Nobody's payout gets cut.

The price of that safety is a lot of locked-up money, which means sellers must charge
more, which means we need to work hard on the seller's side of the market.

Five changes, in the order I'd do them:

| # | Change | Effort | What it buys |
|---|---|---|---|
| 1 | Let the settled number be anything measurable | Tiny | Interest rates, volatility, compute — a real market instead of one product |
| 5 | Fix whole-cent rounding now | Tiny | Stops a bug that would break our core promise |
| 2 | Build the robot seller | Big | Someone to actually trade with |
| 3 | Show sellers their worst day | Small | Cheaper prices, automatically |
| 4 | Interest on the jar + reuse guaranteed money | Medium | Cheaper to be a seller; rollovers stop being painful |

**If we only do one thing: Change 1.** It's nearly free and it changes what this
product *is*.
