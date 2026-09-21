# How netting actually works: three buyers, three sellers

A complete walkthrough with every dollar tracked. No formulas.

Companion to [explainer.md](explainer.md).

---

## The event

One event. Three possible results: **A**, **B**, or **C**. Exactly one of them happens.

Every claim we trade pays **$300** if its result comes up, and **$0** otherwise.

All three results look about equally likely, so a $300 claim costs about **$100**.

## The cast

| Buyers | Sellers |
|---|---|
| Buyer 1 | Seller 1 |
| Buyer 2 | Seller 2 |
| Buyer 3 | Seller 3 |

**Buyers** pay cash now and might get paid later. **Sellers** take cash now and might have
to pay later — so sellers are the ones who have to leave money in the jar.

## The one rule

> **Before any trade is allowed, the jar must hold enough to pay everybody — in every
> single result. Not on average. Every one.**

We'll check this after every round.

---

# Round 1 — three ordinary trades

Three separate deals, nothing clever yet.

| Deal | Buyer pays | Seller promises |
|---|---:|---|
| Buyer 1 ← Seller 1 | $100 | $300 if **A** |
| Buyer 2 ← Seller 2 | $100 | $300 if **B** |
| Buyer 3 ← Seller 3 | $100 | $300 if **C** |

Take Seller 1. They promised $300. They collected $100 from the buyer. So they must add
**$200** of their own to make the jar hold the full $300.

Same for the other two sellers.

| | Buyer put in | Seller put in | Total for this deal |
|---|---:|---:|---:|
| Deal 1 | $100 | $200 | $300 |
| Deal 2 | $100 | $200 | $300 |
| Deal 3 | $100 | $200 | $300 |
| | | | **$900 in the jar** |

### Check the rule

| If this happens | Who gets paid | Total paid out | Jar has |
|---|---|---:|---:|
| A wins | Buyer 1 gets $300, Sellers 2 & 3 get their $300 each back | $900 | $900 |
| B wins | Buyer 2 gets $300, Sellers 1 & 3 get theirs back | $900 | $900 |
| C wins | Buyer 3 gets $300, Sellers 1 & 2 get theirs back | $900 | $900 |

Always exact. Nothing left over, nothing missing.

---

# Round 2 — the netting moment

**Buyer 1 buys a second claim from Seller 1: $300 if B, for $100.**

Now stop and look at Seller 1. They have promised:

- $300 if **A** happens
- $300 if **B** happens

That's **$600 of promises** from one person.

But — **A and B cannot both happen.** Exactly one result wins. So:

| If this happens | Seller 1 owes |
|---|---:|
| A wins | $300 |
| B wins | $300 |
| C wins | $0 |

**The most Seller 1 can ever owe is $300.** Never $600.

So the jar still only needs $300 behind Seller 1's promises. And Seller 1 has now collected
**$200** in premiums ($100 per claim). They only need **$100** of their own money.

They had $200 in. They get **$100 back**.

| Seller 1 | Before round 2 | After round 2 |
|---|---:|---:|
| Promises made | $300 | $600 |
| Most they could ever owe | $300 | **$300** |
| Premiums collected | $100 | $200 |
| **Their own money tied up** | **$200** | **$100** |

**That is netting.** They doubled their business and halved their own money.

### Check the rule again

Buyer 1 added $100, Seller 1 took $100 out. The jar is still **$900**.

| If this happens | Everyone's payouts add to | Jar has |
|---|---:|---:|
| A wins | $900 | $900 |
| B wins | $900 | $900 |
| C wins | $900 | $900 |

Still exact. Nothing was fudged — Seller 1 only took out money the jar genuinely didn't
need any more.

---

# Round 3 — when netting is refused

Now watch the opposite happen.

**Buyer 3 buys from Seller 2: $300 if B *or* C, for $200.** (It covers two results, so it
costs twice as much.)

Seller 2 has now promised:

- $300 if **B** (from round 1)
- $300 if **B or C**

Same $600 of promises as Seller 1. But look:

| If this happens | Seller 2 owes | Why |
|---|---:|---|
| A wins | $0 | neither promise pays |
| B wins | **$600** | **both promises pay!** |
| C wins | $300 | only the second one pays |

**When B wins, both promises come due at once.** The most Seller 2 can owe is **$600**.

They collected $300 in premiums ($100 + $200). So they must put in **$300** of their own —
and the engine demands it before letting the trade through.

The jar grows to **$1,200**.

---

# The whole point, side by side

Both sellers made $600 of promises. Both collected $300 in premiums. Look what the engine
asks of them:

| | Seller 1 | Seller 2 |
|---|---|---|
| Promises made | $300 if A, $300 if B | $300 if B, $300 if B-or-C |
| Can both pay at once? | **No** — A and B are different results | **Yes** — both pay when B wins |
| Worst they could owe | **$300** | **$600** |
| Premiums collected | $200 | $300 |
| **Own money tied up** | **$100** | **$300** |

> **The engine gives no discount for "you made two promises." It works out what you'd owe
> in each result, one at a time, and makes you fund the worst one.**

Seller 1 got a discount because their promises genuinely can't both come due.
Seller 2 didn't, because theirs can.

Nobody decided this. Nobody wrote a rule saying "A and B cancel." The engine just added up
what's owed in each result and looked at the largest number.

---

# Settlement — say B wins

| Who | Holds | Gets paid |
|---|---|---:|
| Buyer 1 | $300 if A, $300 if B | **$300** |
| Buyer 2 | $300 if B | **$300** |
| Buyer 3 | $300 if C, $300 if B-or-C | **$300** |
| Seller 1 | owed on A and B → owes $300 | **$0** |
| Seller 2 | owed on B and B-or-C → owes $600 | **$0** |
| Seller 3 | owed on C → owes nothing | **$300** |
| | | **$1,200 paid out** |

The jar held **$1,200**. It paid out **$1,200**. It is now empty.

## The final scoreboard

| Who | Money in | Money out | Result |
|---|---:|---:|---:|
| Buyer 1 | $200 | $300 | **+$100** |
| Buyer 2 | $100 | $300 | **+$200** |
| Buyer 3 | $300 | $300 | **$0** |
| Seller 1 | $100 | $0 | **−$100** |
| Seller 2 | $300 | $0 | **−$300** |
| Seller 3 | $200 | $300 | **+$100** |

Buyers made **+$300**. Sellers lost **−$300**. They cancel exactly.

**No money was created and none disappeared.** Every dollar a winner took came from a
loser, and the jar was never short by a cent at any moment along the way.

---

# Three things to take away

**1. Sellers put in the gap, not the whole promise.** The jar always holds the full worst
case, but buyers' premiums pay for part of it. The seller only tops up the rest.

**2. Netting isn't a discount — it's just counting properly.** Seller 1 could never owe
$600, so asking for $600 would have been wrong. We ask for what's genuinely at risk.

**3. It only works inside one account.** Seller 1's two promises cancelled because *one
person* held both and genuinely can't owe on both. If two different sellers had made those
two promises, each would fund their own $300 in full — neither controls the other's
position, so neither gets relief.
