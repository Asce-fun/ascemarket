"""Differential, adversarial and lifecycle checks for the research deliverable."""
import copy
import itertools
import random
import unittest

from model_v2.ledger import Fee
from model_v2.schema import Cover, Rejected
from simulations.collateral_engine import (
    MAX_ABS, aggregate, candidate, ctf_allocation, export_account,
    guaranteed_floor, gross_short_cap, minimum_new_cash, payoff, requirement,
)
from simulations.portfolio_examples import (
    COVERS_A, STATES_A, UNIT, base, change, closed_c, execute, fixture,
    opened_a, run, settlement_rows,
)


class StateClearingTests(unittest.TestCase):
    def rejected(self, ledger, changes, nonce, fees=()):
        before = ledger.snapshot()
        with self.assertRaises(Rejected):
            execute(ledger, changes, nonce, fees)
        self.assertEqual(before, ledger.snapshot())
        ledger.audit()

    def test_report_matches_every_terminal_state(self):
        report = run()
        self.assertEqual(report["A"]["state_aware_backing_usdc"], 11000)
        self.assertEqual(report["B"]["state_aware_backing_usdc"], 11000)
        self.assertEqual(report["C"]["remaining_backing_usdc"], 10500)
        for section, backing in (("A", 11000), ("B", 11000), ("C", 10500)):
            for row in report[section]["settlements"]:
                self.assertEqual(sum(row["payout_usdc"].values()), backing)
                self.assertGreaterEqual(min(row["payout_usdc"].values()), 0)

    def test_all_120_claim_orders_at_each_state(self):
        # Five accounts, including an empty fee account; 720 branches across six
        # states. No global holder iteration
        # is required by settlement; each account independently pulls its payout.
        for k in range(len(STATES_A)):
            ledger, _ = opened_a()
            ledger.settle({0: {k}}, "resolver")
            total = ledger.escrow
            for ordering in itertools.permutations(ledger.accounts):
                branch = copy.deepcopy(ledger)
                paid = [branch.claim(who, who) for who in ordering]
                self.assertEqual(sum(paid), total)
                self.assertEqual(branch.escrow, 0)
                branch.audit()

    def test_cash_and_premiums_not_double_counted(self):
        p = (-10000, -11000, 0)
        proposal = candidate(4000, (0, 0, 0), 7000, p)
        self.assertEqual(proposal.deposit_needed, 0)
        self.assertEqual(proposal.floor, 0)
        self.assertEqual(candidate(3999, (0, 0, 0), 7000, p).deposit_needed, 1)
        self.assertEqual(candidate(4000, (0, 0, 0), 7000, p, fee=200).deposit_needed, 200)

    def test_cannot_withdraw_one_base_unit_of_required_backing(self):
        ledger, _ = opened_a()
        self.rejected(ledger, [change(ledger, "maker", external=-1)], "one-unit")

    def test_fees_preserve_conservation_and_cannot_use_locked_cash(self):
        ledger, _ = opened_a()
        self.rejected(ledger, [change(ledger, "maker")], "fee-underfunded",
                      (Fee("maker", "treasury", 1),))
        execute(ledger, [change(ledger, "maker", external=1)], "fee-funded",
                (Fee("maker", "treasury", 1),))
        self.assertEqual(ledger.accounts["treasury"].cash, 1)
        self.assertEqual(ledger.escrow, 11000*UNIT+1)

    def test_partial_close_at_adverse_price_rejects_without_cash(self):
        ledger, ids = opened_a()
        half = ledger.admit(Cover(ledger.market.identifier, "half-C", tuple(
            (0, k, v//2) for k, v in enumerate(base(COVERS_A[2])) if v)))
        self.rejected(ledger, [
            change(ledger, "maker", ((ids[2], 1), (half, -1)), -1000*UNIT),
            change(ledger, "buyer2", ((ids[2], -1), (half, 1)), 1000*UNIT)
        ], "expensive-close")
        execute(ledger, [
            change(ledger, "maker", ((ids[2], 1), (half, -1)), -1000*UNIT, 500*UNIT),
            change(ledger, "buyer2", ((ids[2], -1), (half, 1)), 1000*UNIT)
        ], "funded-close")
        self.assertEqual(ledger.bounds("maker").minimum, 0)

    def test_close_single_cover_need_not_release_backing(self):
        total = aggregate(((1, f) for f in COVERS_A), len(STATES_A))
        remaining = tuple(t-a//2 for t, a in zip(total, COVERS_A[0]))
        self.assertEqual(max(remaining), max(total))

    def test_funded_floor_withdrawal_creates_signed_cash(self):
        ledger, ids = fixture(("low", "high"), ((100, 150),))
        execute(ledger, [change(ledger, "maker", ((ids[0], -1),), external=150*UNIT),
                        change(ledger, "buyer0", ((ids[0], 1),))], "floor-open")
        execute(ledger, [change(ledger, "buyer0", external=-100*UNIT)], "floor-withdraw")
        self.assertEqual(ledger.accounts["buyer0"].cash, -100*UNIT)
        self.assertEqual(ledger.bounds("buyer0").minimum, 0)
        # Selling/exporting the whole nominal claim now removes the guarantee.
        self.assertEqual(export_account(-100, (100, 150), (100, 150)), -100)
        self.rejected(ledger, [change(ledger, "buyer0", ((ids[0], -1),)),
                              change(ledger, "maker", ((ids[0], 1),))], "remove-floor")

    def test_removed_long_hedge_requires_funding(self):
        ledger, ids = fixture(("low", "high"), ((100, 0), (100, 0)))
        execute(ledger, [change(ledger, "maker", ((ids[0], -1), (ids[1], 1))),
                        change(ledger, "buyer0", ((ids[0], 1),)),
                        change(ledger, "buyer1", ((ids[1], -1),), external=100*UNIT)], "hedge")
        self.rejected(ledger, [change(ledger, "maker", ((ids[1], -1),)),
                              change(ledger, "buyer0", ((ids[1], 1),))], "remove-hedge")

    def test_pairwise_savings_cannot_be_summed(self):
        f = ((100, 0, 0), (0, 100, 0), (0, 0, 100))
        p = aggregate(((-1, row) for row in f), 3)
        self.assertEqual(requirement(p), 100)
        self.assertEqual(gross_short_cap(((-1, row) for row in f)), 300)

    def test_same_direction_can_have_zero_saving(self):
        f = ((100, 0), (100, 0), (100, 0))
        self.assertEqual(ctf_allocation(f)["backing"], 300)

    def test_exception_can_dominate_normal_states(self):
        f = ((100, 0, 60), (0, 100, 60))
        self.assertEqual(ctf_allocation(f)["backing"], 120)

    def test_provisional_oracle_does_not_release_cash(self):
        ledger, _ = opened_a()
        ledger.post_report(0, {5}, "resolver")
        self.assertEqual(ledger.bounds("maker").minimum, 0)
        self.rejected(ledger, [change(ledger, "maker", external=-1)], "provisional")

    def test_finality_cannot_widen_or_empty_support(self):
        ledger, _ = opened_a()
        ledger.confirm({0: {2}}, "resolver")
        before = ledger.snapshot()
        for support in ({0: {0}}, {0: set()}):
            with self.assertRaises(Rejected):
                ledger.confirm(support, "resolver")
            self.assertEqual(ledger.snapshot(), before)

    def test_cross_event_definition_is_rejected(self):
        ledger, _ = fixture()
        other, ids = fixture(("low", "high"), ((100, 0),))
        with self.assertRaises(Rejected):
            ledger.admit(other.covers[ids[0]])

    def test_nonconserving_creation_and_stale_revision_are_atomic(self):
        ledger, ids = fixture()
        self.rejected(ledger, [change(ledger, "buyer0", ((ids[0], 1),))], "fake-mint")
        stale = change(ledger, "maker", external=1)
        execute(ledger, [change(ledger, "maker", external=1)], "deposit")
        self.rejected(ledger, [stale], "stale")

    def test_invalid_payoffs_and_overflow_are_rejected(self):
        for bad in ((), (True, 0), (1.5, 0), (-1, 0), (MAX_ABS+1, 0)):
            with self.assertRaises(ValueError):
                payoff(bad)
        with self.assertRaises(ValueError):
            payoff((1, 2), 3)
        with self.assertRaises(ValueError):
            aggregate(((2, (MAX_ABS, 0)),), 2)

    def test_lifecycle_peak_includes_execution_order(self):
        self.assertEqual(minimum_new_cash((0, 0, 0), (30, 40),
                         ((-100, 0, 0), (-100, -100, 0))), 70)
        self.assertEqual(minimum_new_cash((0, 0, 0), (70,), ((-100, -100, 0),)), 30)
        self.assertEqual(minimum_new_cash((0, 0, 0), (70, -90, -90),
                         ((-100, -100, 0), (0, -100, 0), (0, 0, 0))), 120)

    def test_random_ctf_certificate_matches_exact_joint_liability(self):
        rng = random.Random(9302026)
        for _ in range(1000):
            n = rng.randrange(2, 33)
            f = [tuple(rng.randrange(101) for _ in range(n)) for _ in range(rng.randrange(1, 9))]
            result = ctf_allocation(f)
            independent = [sum(row[k] for row in f) for k in range(n)]
            self.assertEqual(result["backing"], max(independent))
            self.assertLessEqual(result["backing"], sum(max(row) for row in f))
            for k in range(n):
                self.assertEqual(result["maker_residual"][k]+independent[k], result["backing"])

    def test_seeded_action_sequences_vs_independent_raw_state_evaluator(self):
        accepted = rejected = 0
        for seed in range(40):
            rng = random.Random(seed)
            states = tuple(f"state{k}" for k in range(8))
            f = tuple(tuple(rng.randrange(11) for _ in states) for _ in range(4))
            ledger, ids = fixture(states, f)
            for step in range(100):
                who = rng.choice(list(ledger.accounts))
                if rng.randrange(3) == 0:
                    external = rng.randint(-50, 50)*UNIT
                    changes = [change(ledger, who, external=external)]
                else:
                    other = rng.choice([x for x in ledger.accounts if x != who])
                    cid = rng.choice(ids)
                    q = rng.choice((-2, -1, 1, 2))
                    cash = rng.randint(-20, 20)*UNIT
                    changes = [change(ledger, who, ((cid, q),), cash),
                               change(ledger, other, ((cid, -q),), -cash)]
                expected = True
                for c in changes:
                    account = ledger.accounts[c.account]
                    holdings = dict(account.holdings)
                    for cid, q in c.holdings:
                        holdings[cid] = holdings.get(cid, 0)+q
                    rows = [base(f[ids.index(cid)]) for cid in holdings]
                    raw = aggregate(zip(holdings.values(), rows), len(states))
                    next_cash = account.cash+c.cash+c.external
                    expected &= guaranteed_floor(next_cash, raw) >= 0
                    expected &= ledger.wallets[c.account]-c.external >= 0
                before = ledger.snapshot()
                try:
                    execute(ledger, changes, f"seed{seed}-step{step}")
                    self.assertTrue(expected)
                    accepted += 1
                except Rejected:
                    self.assertFalse(expected)
                    self.assertEqual(before, ledger.snapshot())
                    rejected += 1
                for account in ledger.accounts.values():
                    raw = aggregate(((q, base(f[ids.index(cid)])) for cid, q in account.holdings), len(states))
                    self.assertEqual(min(raw)+account.cash,
                        min(account.cash+sum(q*base(f[ids.index(cid)])[k] for cid, q in account.holdings)
                            for k in range(len(states))))
                    self.assertGreaterEqual(guaranteed_floor(account.cash, raw), 0)
                ledger.audit()
        self.assertGreater(accepted, 100)
        self.assertGreater(rejected, 100)


if __name__ == "__main__":
    unittest.main()
