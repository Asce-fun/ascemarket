"""Atomic accounting model. Approval objects are NOT cryptographic signatures."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json

from .payoffs import Payoff, VOID, q, total


class Rejected(ValueError):
    pass


def integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


@dataclass(frozen=True)
class Change:
    account: str
    revision: int
    payout: Payoff = Payoff()
    payment: Fraction = Fraction(0)
    cash_flow: Fraction = Fraction(0)

    def __post_init__(self):
        integer(self.revision, "revision")
        if not isinstance(self.payout, Payoff):
            raise TypeError("payout must be a Payoff")
        object.__setattr__(self, "payment", q(self.payment))
        object.__setattr__(self, "cash_flow", q(self.cash_flow))


@dataclass(frozen=True)
class Fee:
    payer: str
    amount: Fraction

    def __post_init__(self):
        object.__setattr__(self, "amount", q(self.amount))
        if self.amount < 0:
            raise ValueError("negative fee")


@dataclass(frozen=True)
class Batch:
    market_id: str
    expires_at: int
    changes: tuple[Change, ...]
    fees: tuple[Fee, ...] = ()

    def __post_init__(self):
        integer(self.expires_at, "expiry")
        object.__setattr__(self, "changes", tuple(self.changes))
        object.__setattr__(self, "fees", tuple(self.fees))
        if not all(isinstance(c, Change) for c in self.changes):
            raise TypeError("invalid change")
        if not all(isinstance(f, Fee) for f in self.fees):
            raise TypeError("invalid fee")

    @property
    def digest(self):
        body = {"schema": "ascemarket-research-batch-v1", "market": self.market_id,
                "expires_at": self.expires_at,
                "changes": [{"account": c.account, "revision": c.revision,
                             "payout": c.payout.encoded(), "payment": str(c.payment),
                             "cash_flow": str(c.cash_flow)} for c in self.changes],
                "fees": [{"payer": f.payer, "amount": str(f.amount)} for f in self.fees]}
        return hashlib.sha256(json.dumps(body, sort_keys=True,
                                         separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Approval:
    account: str
    digest: str


def approve(batch: Batch, account: str) -> Approval:
    """Harness assertion only; this function does not authenticate an owner."""
    return Approval(account, batch.digest)


@dataclass(frozen=True)
class Account:
    balance: Payoff
    revision: int = 0


@dataclass(frozen=True)
class Funding:
    deposit: Fraction
    withdrawable: Fraction


@dataclass(frozen=True)
class Market:
    identifier: str
    asset: str
    close_at: int


class Ledger:
    def __init__(self, market_id="research-price-close", asset="UNIT", close_at=1000):
        self._market = Market(market_id, asset, integer(close_at, "close time"))
        self.now = 0
        self.escrow = Fraction(0)
        self.treasury = "treasury"
        self._accounts = {self.treasury: Account(Payoff())}
        self._wallets = {self.treasury: Fraction(0)}
        self.result = None
        self._redeemed: dict[str, Fraction] = {}
        self._endowments = Fraction(0)

    @property
    def market_id(self):
        return self._market.identifier

    @property
    def asset(self):
        return self._market.asset

    @property
    def close_at(self):
        return self._market.close_at

    def _open(self):
        if self.result is not None or self.now >= self.close_at:
            raise Rejected("market is closed")

    def register(self, account: str, wallet=0):
        self._open()
        if not isinstance(account, str) or not account or account in self._accounts:
            raise Rejected("invalid or existing account")
        wallet = q(wallet)
        if wallet < 0:
            raise Rejected("negative wallet endowment")
        self._accounts[account] = Account(Payoff())
        self._wallets[account] = wallet
        self._endowments += wallet

    def account(self, name):
        try:
            return self._accounts[name]
        except KeyError:
            raise Rejected("unknown account") from None

    def wallet(self, name):
        self.account(name)
        return self._wallets[name]

    @property
    def names(self):
        return tuple(self._accounts)

    def advance(self, now):
        now = integer(now, "time")
        if now < self.now:
            raise Rejected("time cannot go backward")
        self.now = now

    def funding(self, account, payout=Payoff(), payment=0, fee=0):
        self._open()
        fee = q(fee)
        if fee < 0:
            raise ValueError("negative fee")
        minimum = (self.account(account).balance + payout -
                   Payoff.constant(q(payment) + fee)).minimum
        return Funding(max(Fraction(0), -minimum), max(Fraction(0), minimum))

    def execute(self, batch: Batch, approvals):
        self._open()
        if batch.market_id != self.market_id:
            raise Rejected("wrong market")
        if self.now > batch.expires_at:
            raise Rejected("batch expired")
        participants = [c.account for c in batch.changes]
        if not participants or len(set(participants)) != len(participants):
            raise Rejected("empty or duplicate participant changes")
        for change in batch.changes:
            if self.account(change.account).revision != change.revision:
                raise Rejected("stale revision")
        approvals = tuple(approvals)
        digest = batch.digest
        if (len(approvals) != len(participants) or
                {a.account for a in approvals} != set(participants) or
                any(a.digest != digest for a in approvals)):
            raise Rejected("missing or mismatched approval")
        if not total(c.payout for c in batch.changes).is_zero:
            raise Rejected("payout changes do not conserve claims")
        if sum((c.payment for c in batch.changes), Fraction(0)) != 0:
            raise Rejected("premium payments do not conserve cash")
        fees = {name: Fraction(0) for name in participants}
        for fee in batch.fees:
            if fee.payer not in fees:
                raise Rejected("fee payer did not approve a change")
            fees[fee.payer] += fee.amount
        fee_total = sum(fees.values(), Fraction(0))

        # Nothing above or below this line mutates state before all checks pass.
        balances, wallets = {}, {}
        cash_total = Fraction(0)
        for change in batch.changes:
            name = change.account
            balances[name] = (self.account(name).balance + change.payout +
                              Payoff.constant(change.cash_flow - change.payment - fees[name]))
            wallets[name] = self._wallets[name] - change.cash_flow
            cash_total += change.cash_flow
        if fee_total:
            current = balances.get(self.treasury, self.account(self.treasury).balance)
            balances[self.treasury] = current + Payoff.constant(fee_total)
        for name, balance in balances.items():
            if balance.minimum < 0:
                raise Rejected(f"underfunded account: {name}")
        if any(wallet < 0 for wallet in wallets.values()):
            raise Rejected("insufficient external wallet balance")
        new_escrow = self.escrow + cash_total
        if new_escrow < 0:
            raise Rejected("insufficient escrow")
        candidates = {name: Account(balance, self.account(name).revision + 1)
                      for name, balance in balances.items()}

        self._accounts.update(candidates)
        self._wallets.update(wallets)
        self.escrow = new_escrow

    def finalize(self, result):
        if self.result is not None:
            raise Rejected("already finalized")
        if self.now < self.close_at:
            raise Rejected("observation time not reached")
        result = VOID if result == VOID else q(result)
        self.result = result

    def redeem(self, account):
        if self.result is None:
            raise Rejected("not finalized")
        entry = self.account(account)
        if account in self._redeemed:
            raise Rejected("already redeemed")
        amount = entry.balance.value(self.result)
        if amount < 0 or amount > self.escrow:
            raise Rejected("invalid redemption backing")
        self._accounts[account] = Account(Payoff(), entry.revision + 1)
        self._wallets[account] += amount
        self.escrow -= amount
        self._redeemed[account] = amount
        return amount

    def audit(self):
        if self.escrow < 0 or any(w < 0 for w in self._wallets.values()):
            raise AssertionError("negative actual funds")
        if self.result is None:
            if any(a.balance.minimum < 0 for a in self._accounts.values()):
                raise AssertionError("negative future balance")
            if total(a.balance for a in self._accounts.values()) != Payoff.constant(self.escrow):
                raise AssertionError("backing not conserved across all outcomes")
        else:
            unpaid = sum((a.balance.value(self.result) for a in self._accounts.values()),
                         Fraction(0))
            if unpaid != self.escrow:
                raise AssertionError("unredeemed backing mismatch")
        if sum(self._wallets.values(), Fraction(0)) + self.escrow != self._endowments:
            raise AssertionError("external funds not conserved")

    def snapshot(self):
        return {"market": self.market_id, "asset": self.asset, "close_at": self.close_at,
                "now": self.now, "escrow": str(self.escrow),
                "result": None if self.result is None else str(self.result),
                "accounts": {n: {"revision": a.revision, "balance": a.balance.encoded(),
                                  "wallet": str(self._wallets[n])}
                             for n, a in self._accounts.items()},
                "redeemed": {n: str(v) for n, v in self._redeemed.items()}}
