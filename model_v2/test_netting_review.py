"""Targeted netting review: ledger boundaries and independent payout enumeration.

The reserve-account case is an algebraic proxy, NOT an ERC-6909 implementation.
"""
from itertools import combinations, product
import unittest

from .schema import Account, Cover, Market, Rejected
from .ledger import Change, Fee, Ledger, approve
from .verifier import extrema
from . import oracle


class NettingReviewTests(unittest.TestCase):
    def fixture(self, payouts):
        market = Market('netting-review', (tuple(f's{i}' for i in range(len(payouts))),), ())
        ledger = Ledger(market)
        ids = []
        for j in range(len(payouts[0])):
            ids.append(ledger.admit(Cover(market.identifier, f'cover-{j}',
                tuple((0, i, row[j]) for i, row in enumerate(payouts)))))
        for who in ('writer', 'buyer', 'other', 'reserve', 'treasury'):
            ledger.register(who, 10000)
        return ledger, ids

    def change(self, ledger, who, holdings=(), cash=0, external=0):
        return Change(who, ledger.accounts[who].revision, tuple(holdings), cash, external)

    def execute(self, ledger, changes, nonce, fees=()):
        batch = ledger.make_batch(changes, nonce=nonce, fees=fees)
        ledger.execute(batch, [approve(batch, c.account) for c in batch.changes])
        ledger.audit()

    def reject(self, ledger, changes, nonce, fees=()):
        before = ledger.snapshot()
        with self.assertRaises(Rejected):
            self.execute(ledger, changes, nonce, fees)
        self.assertEqual(before, ledger.snapshot())
        ledger.audit()

    def test_joint_payouts_determine_funding_not_cover_ids(self):
        for table, expected in (
            (((0, 0), (100, 0), (0, 100)), 30),
            (((0, 0), (100, 0), (0, 100), (100, 100)), 130),
            (((0, 0), (100, 0), (0, 100), (60, 60)), 50),
        ):
            ledger, ids = self.fixture(table)
            self.assertEqual(ledger.funding('writer', [(c, -1) for c in ids], cash=70)['deposit'], expected)

    def test_shared_backing_cannot_be_withdrawn_or_reused_twice(self):
        ledger, (a, b) = self.fixture(((0, 0), (100, 0), (0, 100)))
        self.execute(ledger, [
            self.change(ledger, 'writer', ((a, -1), (b, -1)), 70, 30),
            self.change(ledger, 'buyer', ((a, 1), (b, 1)), -70, 70),
        ], 'open')
        self.assertEqual(ledger.escrow, 100)
        self.assertEqual(ledger.bounds('writer').minimum, 0)
        self.reject(ledger, [self.change(ledger, 'writer', external=-1)], 'withdraw')
        # Another A increases the worst-case A payout to 200, not 100.
        self.reject(ledger, [
            self.change(ledger, 'writer', ((a, -1),), 30),
            self.change(ledger, 'other', ((a, 1),), -30, 30),
        ], 'reuse')

    def test_different_owners_cannot_share_exclusivity_margin(self):
        ledger, (a, b) = self.fixture(((0, 0), (100, 0), (0, 100)))
        self.reject(ledger, [
            self.change(ledger, 'writer', ((a, -1),), 30, 20),
            self.change(ledger, 'other', ((b, -1),), 40, 10),
            self.change(ledger, 'buyer', ((a, 1), (b, 1)), -70, 70),
        ], 'cross-owner')

    def test_fees_cannot_spend_required_backing(self):
        ledger, (a, b) = self.fixture(((0, 0), (100, 0), (0, 100)))
        self.reject(ledger, [
            self.change(ledger, 'writer', ((a, -1), (b, -1)), 70, 30),
            self.change(ledger, 'buyer', ((a, 1), (b, 1)), -70, 70),
        ], 'fee', (Fee('writer', 'treasury', 1),))

    def test_pairwise_margin_reductions_are_not_additive(self):
        # Every pair is exclusive, but three pairwise savings cannot each be spent.
        ledger, ids = self.fixture(((0, 0, 0), (100, 0, 0), (0, 100, 0), (0, 0, 100)))
        for pair in combinations(ids, 2):
            self.assertEqual(ledger.funding('writer', [(c, -1) for c in pair])['deposit'], 100)
        self.assertEqual(ledger.funding('writer', [(c, -1) for c in ids])['deposit'], 100)
        # Incorrect pairwise subtraction would calculate 300 - 3*100 = 0.

    def test_exporting_a_hedge_requires_residual_account_funding(self):
        ledger, (a, b) = self.fixture(((0, 0), (100, 100)))
        # Same economic payoff, distinct IDs. Writer's +B hedges its -A.
        self.execute(ledger, [
            self.change(ledger, 'writer', ((a, -1), (b, 1))),
            self.change(ledger, 'reserve', ((a, 1),)),
            self.change(ledger, 'other', ((b, -1),), external=100),
        ], 'hedged')
        # Moving B to an algebraic external-reserve proxy removes writer's hedge.
        self.reject(ledger, [
            self.change(ledger, 'writer', ((b, -1),)),
            self.change(ledger, 'reserve', ((b, 1),)),
        ], 'unfunded-export')
        self.execute(ledger, [
            self.change(ledger, 'writer', ((b, -1),), external=100),
            self.change(ledger, 'reserve', ((b, 1),)),
        ], 'funded-export')
        self.assertEqual(ledger.escrow, 200)
        self.assertEqual(ledger.bounds('writer').minimum, 0)

    def test_provisional_report_cannot_release_exception_backing(self):
        ledger, (a, b) = self.fixture(((0, 0), (100, 0), (0, 100), (60, 60)))
        self.execute(ledger, [
            self.change(ledger, 'writer', ((a, -1), (b, -1)), 70, 50),
            self.change(ledger, 'buyer', ((a, 1), (b, 1)), -70, 70),
        ], 'open')
        ledger.post_report(0, {1}, 'resolver')
        self.assertEqual(ledger.bounds('writer').minimum, 0)
        self.reject(ledger, [self.change(ledger, 'writer', external=-20)], 'premature')
        ledger.confirm({0: {1}}, 'resolver')
        self.assertEqual(ledger.bounds('writer').minimum, 20)
        self.execute(ledger, [self.change(ledger, 'writer', external=-20)], 'safe')
        before = ledger.snapshot()
        with self.assertRaises(Rejected):
            ledger.confirm({0: {3}}, 'resolver')
        self.assertEqual(before, ledger.snapshot())
        ledger.audit()

    def test_all_joint_states_and_claim_orders_pay_exactly(self):
        table = ((0, 0), (100, 0), (0, 100), (60, 60))
        for state, payouts in enumerate(table):
            for first in ('writer', 'buyer'):
                ledger, (a, b) = self.fixture(table)
                self.execute(ledger, [
                    self.change(ledger, 'writer', ((a, -1), (b, -1)), 70, 50),
                    self.change(ledger, 'buyer', ((a, 1), (b, 1)), -70, 70),
                ], 'open')
                ledger.settle({0: {state}}, 'resolver')
                expected = {'buyer': sum(payouts), 'writer': 120-sum(payouts)}
                for who in (first, 'buyer' if first == 'writer' else 'writer'):
                    self.assertEqual(ledger.claim(who, who), expected[who])
                    ledger.audit()
                self.assertEqual(ledger.escrow, 0)

    def test_exhaustive_signed_portfolios_match_independent_reference(self):
        ledger, ids = self.fixture(((0, 0, 0), (100, 0, 25), (0, 100, 75), (60, 60, 50)))
        cases = 0
        for mask in range(1, 16):
            support = (frozenset(i for i in range(4) if mask & (1 << i)),)
            for quantities in product(range(-2, 3), repeat=3):
                for cash in (-25, 0, 100):
                    account = Account(cash, tuple(zip(ids, quantities)))
                    actual = extrema(ledger.market, account, ledger.covers, support)
                    expected = oracle.extrema(ledger.market, account, ledger.covers, support)
                    self.assertEqual((actual.minimum, actual.maximum), expected[:2])
                    cases += 1
        self.assertEqual(cases, 5625)


if __name__ == '__main__':
    unittest.main()
