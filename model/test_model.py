"""Accounting and differential checks; these do not establish production security."""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from itertools import permutations
import random
import unittest

from .examples import (HIGH, LOW, automatic_change, change, closing_case, commit,
                       lifecycle, new_book, open_tails)
from .ledger import Batch, Fee, Ledger, Rejected, approve
from .payoffs import Knot, Payoff, VOID, q, total
from .table import Atom, OutcomeTable


def compact(atom):
    if atom.kind == "constant":
        return Payoff.constant(atom.amount)
    if atom.kind in {"step", "below"}:
        return getattr(Payoff, atom.kind)(atom.lower, atom.amount, void=atom.void)
    return getattr(Payoff, atom.kind)(atom.lower, atom.upper, atom.amount, void=atom.void)


class PayoffTests(unittest.TestCase):
    def test_boundary_conventions_and_limits(self):
        cases = [(Payoff.step(3, 7, void=2), [0, 7, 7], 0),
                 (Payoff.below(3, 7, void=2), [7, 0, 0], 7),
                 (Payoff.interval(3, 5, 7, void=2), [0, 7, 0], 0)]
        for payout, values, left in cases:
            self.assertEqual([payout.value(x) for x in (2, 3, 5)], values)
            self.assertEqual(payout.value(3, left_limit=True), left)
            self.assertEqual(payout.value(VOID), 2)
        self.assertEqual(cases[-1][0].value(5, left_limit=True), 7)

    def test_ramp_is_exact_and_has_constant_tails(self):
        ramp = Payoff.ramp(0, 3, 1, void=0)
        self.assertEqual([ramp.value(x) for x in (-100, 0, 1, 2, 3, 100)],
                         [0, 0, F(1, 3), F(2, 3), 1, 1])
        self.assertEqual(ramp.extrema(), (0, 1))

    def test_equivalent_descriptions_normalize_identically(self):
        range_payout = Payoff.interval(2, 7, 3, void=1)
        steps = Payoff.step(2, 3, void=4) - Payoff.step(7, 3, void=3)
        self.assertEqual(range_payout, steps)
        self.assertEqual(range_payout - range_payout, Payoff())
        self.assertEqual(total([steps, -range_payout]), Payoff())
        self.assertEqual((LOW + HIGH) + (-HIGH), LOW)

    def test_jump_left_limit_catches_unattained_minimum(self):
        payout = Payoff.ramp(0, 1, -1, void=0) + Payoff.step(1, 1, void=0)
        self.assertEqual([payout.value(x) for x in (0, 1)], [0, 0])
        self.assertEqual(payout.value(F(999, 1000)), F(-999, 1000))
        self.assertEqual(payout.extrema(), (-1, 0))

    def test_void_can_be_the_binding_worst_outcome(self):
        payout = Payoff.step(3, 7, void=-20) + Payoff.constant(4)
        self.assertEqual(payout.minimum, -16)
        self.assertEqual((payout - Payoff(payout.base, payout.knots, 0)).void, -16)

    def test_invalid_domains_and_inexact_inputs_are_rejected(self):
        for invalid in (0.1, float("nan"), float("inf"), True, None):
            with self.assertRaises(TypeError):
                q(invalid)
        with self.assertRaises(ValueError):
            Payoff(0, (Knot(1, slope_change=1),))
        for constructor in (Payoff.interval, Payoff.ramp):
            with self.assertRaises(ValueError):
                constructor(3, 3, 1, void=0)
        with self.assertRaises(TypeError):
            Payoff.step(3, 1)

    def test_independent_table_has_expected_boundary_semantics(self):
        table = OutcomeTable.from_atoms([Atom("interval", 7, 3, 5, 2)])
        self.assertEqual([table.value(x) for x in (2, 3, 4, 5, VOID)], [0, 7, 7, 0, 2])
        self.assertEqual(table.cells, ((0, 0), (7, 7), (0, 0)))
        self.assertEqual(table.extrema(), (0, 7))

    def test_shared_axis_refinement_preserves_payout(self):
        atoms = [Atom("ramp", 7, 0, 3, 2)]
        original = OutcomeTable.from_atoms(atoms)
        refined = OutcomeTable.from_atoms(atoms, extra_boundaries=[F(i, 17) for i in range(-50, 90)])
        for x in [F(i, 13) for i in range(-60, 120)] + [VOID]:
            self.assertEqual(original.value(x), refined.value(x))
        self.assertEqual(original.extrema(), refined.extrema())
        self.assertGreater(refined.stored_values, original.stored_values)

    def test_250_random_portfolios_against_independent_interval_table(self):
        rng = random.Random(20260917)
        for trial in range(250):
            atoms = []
            for _ in range(rng.randint(1, 12)):
                kind = rng.choice(["constant", "step", "below", "interval", "ramp"])
                amount = F(rng.randint(-40, 40), rng.randint(1, 7))
                lower = F(rng.randint(-20, 20), rng.randint(1, 5))
                upper = lower + F(rng.randint(1, 20), rng.randint(1, 7))
                void = amount if kind == "constant" else F(rng.randint(-9, 9), 3)
                atoms.append(Atom(kind, amount, lower, upper, void))
            payout = total(compact(a) for a in atoms)
            table = OutcomeTable.from_atoms(atoms, extra_boundaries=[F(1, 1009), 0])
            boundaries = table.boundaries
            points = [boundaries[0] - 100, boundaries[-1] + 100, VOID]
            points += list(boundaries)
            points += [(a + b) / 2 for a, b in zip(boundaries, boundaries[1:])]
            with self.subTest(trial=trial):
                self.assertEqual(payout.extrema(), table.extrema())
                for x in points:
                    self.assertEqual(payout.value(x), table.value(x))
                for index, boundary in enumerate(boundaries):
                    self.assertEqual(payout.value(boundary, left_limit=True), table.cells[index][1])


class LedgerTests(unittest.TestCase):
    def batch(self, book, *changes, **kwargs):
        return Batch(kwargs.pop("market_id", book.market_id),
                     kwargs.pop("expires_at", book.now + 100), changes, **kwargs)

    def rejection_preserves_state(self, book, batch, approvals=None):
        before = book.snapshot()
        if approvals is None:
            approvals = [approve(batch, c.account) for c in batch.changes]
        with self.assertRaises(Rejected):
            book.execute(batch, approvals)
        self.assertEqual(book.snapshot(), before)
        book.audit()

    def test_full_lifecycle_and_both_settlement_branches(self):
        book, report = lifecycle()
        self.assertEqual([r["escrow"] for r in report["rows"]], [100, 100, 105, 100, 51])
        self.assertEqual([r["maker_net_cash_in"] for r in report["rows"]], [78, 46, 46, 41, 19])
        self.assertTrue(report["unrelated_accounts_unchanged"])
        self.assertEqual(report["settlement"]["100"]["payouts"],
                         {"maker": 30, "range_buyer": 20, "low_buyer": 0,
                          "high_buyer": 0, "treasury": 1})
        self.assertEqual(report["settlement"][VOID]["payouts"]["maker"], 50)
        self.assertEqual(report["settlement"][VOID]["escrow"], 0)
        book.audit()

    def test_unsafe_partial_exit_rejected_and_funded_exit_accepted(self):
        book, _ = open_tails()
        batch = self.batch(book, change(book, "maker", LOW, 22),
                           change(book, "low_buyer", -LOW, -22, -22))
        self.assertEqual(book.funding("maker", LOW, 22).deposit, 22)
        self.rejection_preserves_state(book, batch)
        commit(book, change(book, "maker", LOW, 22, 22),
               change(book, "low_buyer", -LOW, -22, -22))
        self.assertEqual(book.account("maker").balance, Payoff.constant(100) - HIGH)

    def test_atomic_and_sliced_sequential_funding_comparison(self):
        self.assertEqual(closing_case()["peak_additional_maker_cash"], 22)
        self.assertEqual(closing_case(high_first=True)["peak_additional_maker_cash"], 32)
        self.assertEqual(closing_case(slices=10)["peak_additional_maker_cash"], F(22, 10))
        self.assertEqual(closing_case(slices=100)["peak_additional_maker_cash"], F(22, 100))
        atomic = closing_case(atomic=True)
        self.assertEqual(atomic["peak_additional_maker_cash"], 0)
        self.assertEqual(atomic["executions"], 1)
        self.assertEqual(atomic["maker_final_wallet"], 500)

    def test_unbalanced_numeric_or_void_claims_are_rejected(self):
        book = new_book()
        for payout in (LOW, Payoff(0, (), 1)):
            self.rejection_preserves_state(book, self.batch(book, change(book, "maker", payout)))

    def test_premium_mismatch_is_rejected(self):
        book = new_book()
        self.rejection_preserves_state(book, self.batch(book, change(book, "maker", payment=-1)))

    def test_deposits_cannot_overdraw_wallet(self):
        book = new_book()
        self.rejection_preserves_state(book, self.batch(book, change(book, "maker", cash=501)))

    def test_withdrawal_must_be_safe_on_void_too(self):
        book = new_book()
        claim = Payoff(1, (), 0)
        commit(book, change(book, "maker", -claim, cash=1),
               change(book, "low_buyer", claim))
        self.assertEqual(book.account("low_buyer").balance.value(10), 1)
        self.assertEqual(book.funding("low_buyer").withdrawable, 0)
        self.rejection_preserves_state(book, self.batch(book, change(book, "low_buyer", cash=-1)))

    def test_duplicate_unknown_and_empty_participants_rejected(self):
        book = new_book()
        item = change(book, "maker")
        for changes in ((), (item, item), (replace(item, account="unknown"),)):
            self.rejection_preserves_state(book, self.batch(book, *changes))

    def test_missing_duplicate_and_wrong_approvals_rejected(self):
        book = new_book()
        batch = self.batch(book, change(book, "maker"), change(book, "low_buyer"))
        maker = approve(batch, "maker")
        for approvals in ([], [maker], [maker, maker], [maker, approve(batch, "high_buyer")]):
            self.rejection_preserves_state(book, batch, approvals)

    def test_approved_payload_cannot_change(self):
        book = new_book()
        batch = self.batch(book, change(book, "maker", -LOW, -22, 78),
                           change(book, "low_buyer", LOW, 22, 22))
        approvals = [approve(batch, c.account) for c in batch.changes]
        mutations = [replace(batch, fees=(Fee("maker", 1),)),
                     replace(batch, expires_at=batch.expires_at + 1),
                     replace(batch, market_id="other"),
                     replace(batch, changes=(replace(batch.changes[0], cash_flow=79), batch.changes[1])),
                     replace(batch, changes=(replace(batch.changes[0], payment=-21), batch.changes[1])),
                     replace(batch, changes=(replace(batch.changes[0], payout=-HIGH), batch.changes[1])),
                     replace(batch, changes=(replace(batch.changes[0], payout=Payoff(-100, (), -100)), batch.changes[1]))]
        for mutated in mutations:
            self.assertNotEqual(batch.digest, mutated.digest)
            self.rejection_preserves_state(book, mutated, approvals)

    def test_replay_and_concurrent_stale_changes_rejected(self):
        book = new_book()
        stale = self.batch(book, change(book, "maker", cash=1))
        executed = commit(book, change(book, "maker", cash=2))
        self.rejection_preserves_state(book, executed)
        self.rejection_preserves_state(book, stale)

    def test_deadline_and_close_are_enforced(self):
        book = new_book()
        expired = self.batch(book, change(book, "maker"), expires_at=10)
        book.advance(11)
        self.rejection_preserves_state(book, expired)
        valid = self.batch(book, change(book, "maker"), expires_at=book.close_at + 1)
        book.advance(book.close_at)
        self.rejection_preserves_state(book, valid)
        with self.assertRaises(Rejected):
            book.advance(1)

    def test_fee_backing_treasury_credit_and_authorized_withdrawal(self):
        book = new_book()
        commit(book, change(book, "maker", cash=1), fees=(Fee("maker", 1),))
        self.assertEqual(book.account("treasury").revision, 1)
        self.assertEqual(book.account("treasury").balance, Payoff.constant(1))
        self.rejection_preserves_state(book, self.batch(book, change(book, "treasury", cash=-1)), [])
        commit(book, change(book, "treasury", cash=-1))
        self.assertEqual(book.wallet("treasury"), 1)
        self.assertEqual(book.escrow, 0)

    def test_fee_requires_payer_and_cannot_overdraw_payer(self):
        book = new_book()
        for payer in ("maker", "low_buyer"):
            self.rejection_preserves_state(book, self.batch(book, change(book, "maker"),
                                                            fees=(Fee(payer, 1),)))
        with self.assertRaises(ValueError):
            Fee("maker", -1)

    def test_rational_premiums_fees_and_settlement_conserve_exactly(self):
        book = new_book()
        payout = Payoff.ramp(0, 3, F(1, 3), void=F(1, 9))
        premium, fee = F(1, 7), F(1, 11)
        commit(book, change(book, "maker", -payout, -premium, F(1, 3) - premium + fee),
               change(book, "low_buyer", payout, premium, premium), fees=(Fee("maker", fee),))
        book.advance(book.close_at)
        book.finalize(1)
        self.assertEqual(book.redeem("low_buyer"), F(1, 9))
        self.assertEqual(book.redeem("maker"), F(2, 9))
        self.assertEqual(book.redeem("treasury"), fee)
        self.assertEqual(book.escrow, 0)
        book.audit()

    def test_finalization_and_redemption_are_one_way(self):
        book, _ = open_tails()
        before = book.snapshot()
        for action in (lambda: book.finalize(100), lambda: book.redeem("maker")):
            with self.assertRaises(Rejected):
                action()
            self.assertEqual(book.snapshot(), before)
        book.advance(book.close_at)
        book.finalize(VOID)
        with self.assertRaises(Rejected):
            book.finalize(100)
        book.redeem("maker")
        before = book.snapshot()
        with self.assertRaises(Rejected):
            book.redeem("maker")
        self.assertEqual(book.snapshot(), before)
        with self.assertRaises(Rejected):
            book.register("late", 1)
        book.audit()

    def test_redemption_order_and_boundary_results_preserve_backing(self):
        book, _ = lifecycle()
        # All 120 redemption orders at all discontinuities, an interior, and VOID.
        for result in (94, 95, 97, 100, 103, 105, 106, VOID):
            for order in permutations(book.names):
                branch = deepcopy(book)
                branch.advance(branch.close_at)
                branch.finalize(result)
                for name in order:
                    branch.redeem(name)
                    branch.audit()
                self.assertEqual(branch.escrow, 0)

    def test_market_configuration_cannot_change_through_public_fields(self):
        book = new_book()
        for field, value in (("market_id", "other"), ("asset", "OTHER"), ("close_at", 2000)):
            with self.assertRaises(AttributeError):
                setattr(book, field, value)

    def test_100_random_atomic_transfers_preserve_all_outcome_backing(self):
        rng = random.Random(61017)
        book = Ledger()
        names = ("alice", "bob", "carol")
        for name in names:
            book.register(name, 100000)
        for _ in range(100):
            sender, receiver = rng.sample(names, 2)
            lo = F(rng.randint(-10, 10), 3)
            amount = F(rng.randint(1, 40), 7)
            payout = Payoff.ramp(lo, lo + F(2, 3), amount, void=amount / 3)
            premium, fee = amount / 5, F(1, 101)
            untouched = {n: book.account(n) for n in names if n not in {sender, receiver}}
            funding = book.funding(sender, -payout, -premium, fee)
            commit(book, change(book, sender, -payout, -premium, funding.deposit - funding.withdrawable),
                   automatic_change(book, receiver, payout, premium), fees=(Fee(sender, fee),))
            for name, old in untouched.items():
                self.assertEqual(book.account(name), old)
            book.audit()
        book.advance(book.close_at)
        book.finalize(F(1, 3))
        for name in book.names:
            book.redeem(name)
            book.audit()
        self.assertEqual(book.escrow, 0)


if __name__ == "__main__":
    unittest.main()
