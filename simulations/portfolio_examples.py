"""Reproduce docs/06-examples.md against the existing atomic graph ledger."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from model_v2.ledger import Change, Fee, Ledger, approve
from model_v2.schema import Cover, Market
from simulations.collateral_engine import aggregate, candidate, ctf_allocation, requirement

UNIT = 1_000_000
ROOT = Path(__file__).resolve().parents[1]
STATES_A = ("x<80000", "80000<=x<100000", "100000<=x<120000",
            "120000<=x<150000", "x>=150000", "INVALID")
COVERS_A = ((10000, 6000, 2000, 0, 0, 0),
            (0, 0, 2000, 7000, 10000, 0),
            (1000, 5000, 6000, 4000, 0, 0))
PREMIUMS_A = (2300, 2600, 2100)
STATES_B = ("x<80000", "80000<=x<100000", "100000<=x<120000",
            "x=120000", "120000<x<150000", "x>=150000", "INVALID")
COVERS_B = ((4000, 0, 0, 0, 0, 0, 0),
            (6000, 6000, 0, 0, 0, 0, 0),
            (0, 5000, 5000, 0, 0, 0, 0),
            (0, 0, 0, 0, 7000, 7000, 0))


def base(values):
    return tuple(value * UNIT for value in values)


def usd(amount):
    assert amount % UNIT == 0
    return amount // UNIT


def fixture(states=STATES_A, covers=COVERS_A):
    market = Market("single-expiry-research", (tuple(states),), ())
    ledger = Ledger(market)
    ids = tuple(ledger.admit(Cover(market.identifier, f"cover-{j}",
                tuple((0, k, v) for k, v in enumerate(base(f)) if v)))
                for j, f in enumerate(covers))
    for who in ("maker", *(f"buyer{j}" for j in range(len(ids))), "treasury"):
        ledger.register(who, 100000 * UNIT)
    return ledger, ids


def change(ledger, who, holdings=(), cash=0, external=0):
    return Change(who, ledger.accounts[who].revision, tuple(holdings), cash, external)


def execute(ledger, changes, nonce, fees=()):
    batch = ledger.make_batch(tuple(changes), nonce=nonce, fees=fees)
    ledger.execute(batch, [approve(batch, c.account) for c in batch.changes])
    ledger.audit()


def opened_a(maker_deposit=4000, maker_fee=0):
    ledger, ids = fixture()
    changes = [change(ledger, "maker", tuple((cid, -1) for cid in ids),
                      sum(PREMIUMS_A)*UNIT, maker_deposit*UNIT)]
    changes.extend(change(ledger, f"buyer{j}", ((cid, 1),), -premium*UNIT, premium*UNIT)
                   for j, (cid, premium) in enumerate(zip(ids, PREMIUMS_A)))
    fees = (Fee("maker", "treasury", maker_fee*UNIT),) if maker_fee else ()
    execute(ledger, changes, "open", fees)
    return ledger, ids


def settlement_rows(factory, states):
    rows = []
    for k, state in enumerate(states):
        ledger, _ = factory()
        ledger.settle({0: {k}}, "resolver")
        paid = {}
        # Use a different claim order on alternating states.
        owners = list(ledger.accounts)
        if k % 2:
            owners.reverse()
        for who in owners:
            paid[who] = usd(ledger.claim(who, who))
            ledger.audit()
        assert ledger.escrow == 0
        rows.append({"state": state, "payout_usdc": paid})
    return rows


def example_a():
    ledger, _ = opened_a()
    allocation = ctf_allocation(COVERS_A)
    assert usd(ledger.escrow) == allocation["backing"] == 11000
    assert ledger.bounds("maker").minimum == 0
    # Sequential execution checks actual capital flow rather than just final margin.
    seq, ids = fixture()
    for j, (cid, premium) in enumerate(zip(ids, PREMIUMS_A)):
        execute(seq, [change(seq, "maker", ((cid, -1),), premium*UNIT,
                            7700*UNIT if j == 0 else 0),
                      change(seq, f"buyer{j}", ((cid, 1),), -premium*UNIT, premium*UNIT)], f"seq{j}")
        free = seq.bounds("maker").minimum
        if free:
            execute(seq, [change(seq, "maker", external=-free)], f"withdraw{j}")
    assert usd(seq.net_deposits["maker"]) == 4000
    return {"states": STATES_A, "covers_usdc": COVERS_A,
            "aggregate_usdc": allocation["aggregate_liability"],
            "gross_cap_usdc": 26000, "state_aware_backing_usdc": 11000,
            "capital_saved_usdc": 15000, "premiums_usdc": PREMIUMS_A,
            "atomic_maker_contribution_usdc": 4000,
            "sequential_maker_peak_usdc": 7700,
            "ctf_atomic_claim_allocation": allocation,
            "settlements": settlement_rows(opened_a, STATES_A)}


def opened_b():
    ledger, ids = fixture(STATES_B, COVERS_B)
    execute(ledger, [change(ledger, "maker", tuple((cid, -1) for cid in ids), external=11000*UNIT),
                    *(change(ledger, f"buyer{j}", ((cid, 1),)) for j, cid in enumerate(ids))], "nested")
    return ledger, ids


def example_b():
    ledger, _ = opened_b()
    liability = aggregate(((1, f) for f in COVERS_B), len(STATES_B))
    assert usd(ledger.escrow) == max(liability) == 11000
    return {"states": STATES_B, "covers_usdc": COVERS_B,
            "aggregate_usdc": liability, "gross_cap_usdc": 22000,
            "state_aware_backing_usdc": 11000, "capital_saved_usdc": 11000,
            "premiums_usdc": [0]*4,
            "settlements": settlement_rows(opened_b, STATES_B)}


def closed_c():
    ledger, ids = opened_a()
    # Half of the original C is an exact separate lot definition, not rounded q.
    half = ledger.admit(Cover(ledger.market.identifier, "half-C",
                 tuple((0, k, v//2) for k, v in enumerate(base(COVERS_A[2])) if v)))
    execute(ledger, [change(ledger, "maker", ((ids[2], 1), (half, -1)), -400*UNIT),
                    change(ledger, "buyer2", ((ids[2], -1), (half, 1)), 400*UNIT)], "partial-close")
    assert ledger.bounds("buyer2").minimum == 400*UNIT
    assert ledger.bounds("maker").minimum == 100*UNIT
    execute(ledger, [change(ledger, "maker", external=-100*UNIT),
                    change(ledger, "buyer2", external=-400*UNIT)], "close-withdraw")
    return ledger, ids


def example_c():
    initial = aggregate(((1, f) for f in COVERS_A), len(STATES_A))
    liability = tuple(total-c//2 for total, c in zip(initial, COVERS_A[2]))
    initial_p = tuple(-x for x in initial)
    delta = tuple(x//2 for x in COVERS_A[2])
    favorable = candidate(11000, initial_p, -400, delta)
    adverse = candidate(11000, initial_p, -1000, delta)
    assert requirement(tuple(-v for v in liability)) == 10500
    assert favorable.floor == 100 and adverse.deposit_needed == 500
    return {"remaining_liability_usdc": liability, "remaining_backing_usdc": 10500,
            "gross_backing_reduction_usdc": 500, "buyback_price_usdc": 400,
            "actual_maker_withdrawal_usdc": 100,
            "adverse_buyback_price_usdc": 1000, "adverse_topup_required_usdc": 500,
            "settlements": settlement_rows(closed_c, STATES_A)}


def example_d():
    prefunded, _ = opened_a(maker_deposit=11000)
    efficient, _ = opened_a()
    fee_case, _ = opened_a(maker_deposit=4200, maker_fee=200)
    assert prefunded.bounds("maker").minimum == 7000*UNIT
    assert efficient.bounds("maker").minimum == 0
    assert fee_case.bounds("maker").minimum == 0 and fee_case.accounts["treasury"].cash == 200*UNIT
    return {"premiums_received_usdc": 7000,
            "prefunded_maker_cash_usdc": usd(prefunded.accounts["maker"].cash),
            "prefunded_free_usdc": usd(prefunded.bounds("maker").minimum),
            "minimal_contribution_usdc": 4000, "minimal_account_free_usdc": 0,
            "with_200_maker_fee_contribution_usdc": 4200,
            "fee_recipient_cash_usdc": 200}


def run():
    return {"scope": "Exact integer single-event model; synthetic premiums; no deployed custody.",
            "date": "2026-09-30", "collateral_base_units_per_usdc": UNIT,
            "A": example_a(), "B": example_b(), "C": example_c(), "D": example_d(),
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), ROOT/"simulations/collateral_engine.py",
                                        ROOT/"model_v2/ledger.py", ROOT/"model_v2/verifier.py")}}


if __name__ == "__main__":
    output = ROOT/"simulations/results.json"
    output.write_text(json.dumps(run(), indent=2)+"\n")
    print("A: 26,000 -> 11,000 USDC backing; 15,000 saved; CTF certificate matches")
    print("B: 22,000 -> 11,000 USDC backing; 11,000 saved")
    print("C: half-C close releases 500 backing; 400 buyback leaves 100 free")
    print("D: 7,000 premium withdrawable with pre-funding; zero with minimal maker funding")
    print(f"Wrote {output.relative_to(ROOT)}")
