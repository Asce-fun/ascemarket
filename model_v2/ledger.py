"""Atomic v2 research ledger.

Approval/actor values are test-harness assertions, NOT cryptographic signatures.
Wallets and token transfers are simulated exact balances, not a custody system.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from fractions import Fraction
from types import MappingProxyType

from .schema import Account, Cover, Market, Rejected, digest, integer, name
from .verifier import extrema, validate_support


@dataclass(frozen=True)
class Change:
    account: str
    revision: int
    holdings: tuple[tuple[str, int], ...] = ()
    cash: int = 0  # signed internal transfer, excluding fees/external funding
    external: int = 0  # positive deposit, negative withdrawal to own wallet

    def __post_init__(self):
        name(self.account)
        integer(self.revision, "revision", minimum=0)
        integer(self.cash)
        integer(self.external)
        object.__setattr__(self, "holdings", Account(holdings=self.holdings).holdings)


@dataclass(frozen=True)
class Fee:
    payer: str
    recipient: str
    amount: int

    def __post_init__(self):
        name(self.payer)
        name(self.recipient)
        integer(self.amount, "fee", minimum=0)
        if self.payer == self.recipient:
            raise Rejected("self fee")


@dataclass(frozen=True)
class Batch:
    market: str
    epoch: int
    nonce: str
    expires: int
    changes: tuple[Change, ...]
    fees: tuple[Fee, ...] = ()

    def __post_init__(self):
        name(self.market)
        name(self.nonce)
        integer(self.epoch, "epoch", minimum=0)
        integer(self.expires, "expiry", minimum=0)
        object.__setattr__(self, "changes", tuple(self.changes))
        object.__setattr__(self, "fees", tuple(self.fees))
        if not self.changes or not all(isinstance(c,Change) for c in self.changes):
            raise Rejected("invalid changes")
        if not all(isinstance(f,Fee) for f in self.fees):
            raise Rejected("invalid fees")
        if len({c.account for c in self.changes}) != len(self.changes):
            raise Rejected("duplicate participant")

    @property
    def digest(self):
        return digest({"type":"package-v2", **asdict(self)})


@dataclass(frozen=True)
class Approval:
    account: str
    digest: str


def approve(payload, account):
    """Harness assertion. Anyone in Python can construct it; NOT authentication."""
    return Approval(account, payload.digest)


@dataclass(frozen=True)
class Order:
    market: str
    maker: str
    cover: str
    side: str  # maker 'sell' or 'buy'
    quantity: int
    unit_price: int
    min_fill: int
    expires: int
    epoch: int
    nonce: str

    def __post_init__(self):
        for key in ("market","maker","cover","nonce"):
            name(getattr(self,key))
        if self.side not in ("buy","sell"):
            raise Rejected("invalid order side")
        integer(self.quantity,"quantity",minimum=1)
        integer(self.unit_price,"price",minimum=0)
        integer(self.min_fill,"minimum fill",minimum=1,maximum=self.quantity)
        integer(self.expires,"expiry",minimum=0)
        integer(self.epoch,"epoch",minimum=0)

    @property
    def digest(self):
        return digest({"type":"standing-order-v2", **asdict(self)})


@dataclass(frozen=True)
class Fill:
    order: str
    taker: str
    revision: int
    quantity: int
    external: int
    epoch: int
    nonce: str
    expires: int

    def __post_init__(self):
        for key in ("order","taker","nonce"):
            name(getattr(self,key))
        integer(self.revision,"revision",minimum=0)
        integer(self.quantity,"quantity",minimum=1)
        integer(self.external,"external")
        integer(self.epoch,"epoch",minimum=0)
        integer(self.expires,"expiry",minimum=0)

    @property
    def digest(self):
        return digest({"type":"fill-v2", **asdict(self)})


class Ledger:
    def __init__(self, market: Market):
        self.market=market
        self._covers={}
        self._accounts={}
        self._wallets={}
        self._net={}
        self._support=market.full_support
        self._resolved={}
        self._reports={}
        self._orders={}
        self._order_nonces=set()
        self._filled={}
        self._cancelled=set()
        self._used=set()
        self._claimed=set()
        self._receipts=[]
        self.epoch=0
        self.now=0
        self.escrow=0
        self.endowment=0
        self.status="open"

    @property
    def covers(self): return MappingProxyType(self._covers)
    @property
    def accounts(self): return MappingProxyType(self._accounts)
    @property
    def wallets(self): return MappingProxyType(self._wallets)
    @property
    def resolved(self): return MappingProxyType(self._resolved)
    @property
    def support(self): return self._support
    @property
    def net_deposits(self): return MappingProxyType(self._net)
    @property
    def receipts(self): return tuple(self._receipts)

    def _auth(self, actual, expected):
        if actual != expected:
            raise Rejected("unauthorized harness actor")

    def _account(self, who):
        if who not in self._accounts:
            raise Rejected("unknown account")
        return self._accounts[who]

    def register(self, who, wallet=0):
        name(who)
        integer(wallet,"wallet",minimum=0,maximum=self.market.limits.max_abs)
        if who in self._accounts or self.status=="settled":
            raise Rejected("invalid registration")
        endowment=self.market.limits.checked(self.endowment+wallet)
        self._accounts[who]=Account()
        self._wallets[who]=wallet
        self._net[who]=0
        self.endowment=endowment

    def admit(self, cover, actor="admin"):
        self._auth(actor,self.market.admin)
        if self.status=="settled" or self.now>=self.market.close_at:
            raise Rejected("market closed")
        if not isinstance(cover,Cover):
            raise Rejected("invalid cover")
        cover.validate(self.market)
        cid=cover.identifier
        if cid in self._covers or len(self._covers)>=self.market.limits.max_covers:
            raise Rejected("duplicate cover or catalogue limit")
        resolution_bound=self.market.work*(len(self._covers)+2)
        resolution_bound+=len(cover.nodes)+len(cover.edges)
        resolution_bound+=sum(len(c.nodes)+len(c.edges) for c in self._covers.values())
        if resolution_bound>self.market.limits.max_fact_work:
            raise Rejected("catalogue exceeds finalization work budget")
        if cover.trade_until<=self.now or cover.trade_until>self.market.close_at:
            raise Rejected("invalid cover trading window")
        # Cover semantics are defined over the full graph, not just current support.
        extrema(self.market,Account(holdings=((cid,1),)),{cid:cover})
        current=extrema(self.market,Account(holdings=((cid,1),)),{cid:cover},self.support)
        if current.minimum==current.maximum:
            raise Rejected("cannot issue already resolved cover")
        self._covers[cid]=cover
        return cid

    def advance(self, now):
        integer(now,"clock",minimum=self.now)
        self.now=now

    def _materialized(self, account):
        cash=account.cash
        holdings=[]
        for cid,q in account.holdings:
            if cid in self._resolved:
                cash=self.market.limits.checked(cash+self.market.limits.checked(q*self._resolved[cid]))
            else:
                holdings.append((cid,q))
        return Account(cash,tuple(holdings),account.revision)

    def materialize(self, who, actor):
        self._auth(actor,who)
        old=self._account(who)
        new=self._materialized(old)
        if new != old:
            self._accounts[who]=replace(new,revision=old.revision+1)
        return self._accounts[who]

    def bounds(self, who):
        return extrema(self.market,self._account(who),self._covers,self.support)

    def make_batch(self, changes, *, fees=(), nonce, expires=None):
        return Batch(self.market.identifier,self.epoch,nonce,
                     self.now+100 if expires is None else expires,tuple(changes),tuple(fees))

    def _candidate(self,batch):
        if batch.market!=self.market.identifier or batch.epoch!=self.epoch:
            raise Rejected("wrong market or stale epoch")
        if self.status=="settled" or self.now>=batch.expires:
            raise Rejected("settled or expired")
        touched={c.account for c in batch.changes}|{f.recipient for f in batch.fees}
        lim=self.market.limits
        if len(batch.fees)>lim.max_fees:
            raise Rejected("batch fee limit")
        if len(touched)>lim.max_batch_accounts:
            raise Rejected("batch account limit")
        if self.market.work*len(touched)>lim.max_batch_work:
            raise Rejected("batch graph work limit")
        by_name={c.account:c for c in batch.changes}
        candidates={who:self._materialized(self._account(who)) for who in touched}
        wallets={who:self._wallets[who] for who in touched}
        net={who:self._net[who] for who in touched}
        total_cash=0
        total_external=0
        total_lots={}
        for change in batch.changes:
            old=self._account(change.account)
            if change.revision!=old.revision:
                raise Rejected("stale account revision")
            if change.holdings or change.cash or batch.fees:
                if self.status!="open" or self.now>=self.market.close_at:
                    raise Rejected("trading paused or closed")
            account=candidates[change.account]
            lots=dict(account.holdings)
            for cid,q in change.holdings:
                lim.checked(q)
                if cid not in self._covers or cid in self._resolved:
                    raise Rejected("unknown or resolved cover")
                if self.now>=self._covers[cid].trade_until:
                    raise Rejected("cover trading closed")
                lots[cid]=lim.checked(lots.get(cid,0)+q)
                total_lots[cid]=lim.checked(total_lots.get(cid,0)+q)
            total_cash=lim.checked(total_cash+lim.checked(change.cash))
            total_external=lim.checked(total_external+lim.checked(change.external))
            cash=lim.checked(lim.checked(account.cash+change.cash)+change.external)
            wallet=lim.checked(wallets[change.account]-change.external)
            if wallet<0:
                raise Rejected("insufficient wallet funds")
            wallets[change.account]=wallet
            net[change.account]=lim.checked(net[change.account]+change.external)
            candidates[change.account]=Account(cash,tuple(lots.items()),old.revision)
        if total_cash or any(total_lots.values()):
            raise Rejected("nonconserving batch")
        for fee in batch.fees:
            lim.checked(fee.amount)
            if fee.payer not in by_name:
                raise Rejected("fee payer must authorize")
            payer=candidates[fee.payer]
            recipient=candidates[fee.recipient]
            candidates[fee.payer]=replace(payer,cash=lim.checked(payer.cash-fee.amount))
            candidates[fee.recipient]=replace(recipient,cash=lim.checked(recipient.cash+fee.amount))
        escrow=lim.checked(self.escrow+total_external)
        if escrow<0:
            raise Rejected("negative escrow")
        minima={}
        work=0
        for who in sorted(touched):
            result=extrema(self.market,candidates[who],self._covers,self.support)
            work+=result.work
            if work>lim.max_batch_work:
                raise Rejected("batch verification work limit")
            if result.minimum<0:
                raise Rejected(f"underfunded account: {who}")
            minima[who]=result.minimum
            candidates[who]=replace(candidates[who],revision=self._accounts[who].revision+1)
        return candidates,wallets,net,escrow,minima,work

    def preview(self,batch):
        _,_,_,escrow,minima,work=self._candidate(batch)
        return {"epoch":self.epoch,"digest":batch.digest,"escrow_after":escrow,
                "withdrawable_after":minima,"verification_work":work}

    def _commit(self,batch,key,prepared):
        candidates,wallets,net,escrow,minima,work=prepared
        # All validation precedes this no-failure in-memory commit section.
        self._accounts.update(candidates)
        self._wallets.update(wallets)
        self._net.update(net)
        self.escrow=escrow
        self._used.add(key)
        receipt=(key,batch.digest,self.epoch,tuple(sorted(minima.items())),work)
        self._receipts.append(receipt)
        return receipt

    def execute(self,batch,approvals):
        key="package:"+batch.digest
        if key in self._used:
            raise Rejected("replayed package")
        expected={Approval(c.account,batch.digest) for c in batch.changes}
        if set(approvals)!=expected:
            raise Rejected("missing or mismatched approval")
        return self._commit(batch,key,self._candidate(batch))

    def funding(self,who,holdings=(),cash=0,fee=0):
        """Pure exact preview before external funding; not an executable quote."""
        integer(cash)
        integer(fee,"fee",minimum=0)
        account=self._materialized(self._account(who))
        lots=dict(account.holdings)
        for cid,q in Account(holdings=holdings).holdings:
            if cid not in self._covers or cid in self._resolved:
                raise Rejected("unknown or resolved cover")
            lots[cid]=self.market.limits.checked(lots.get(cid,0)+q)
        candidate=Account(self.market.limits.checked(account.cash+cash-fee),tuple(lots.items()))
        result=extrema(self.market,candidate,self._covers,self.support)
        return {"minimum":result.minimum,"deposit":max(0,-result.minimum),
                "withdrawable":max(0,result.minimum),"witness":result.witness}

    def post_report(self,checkpoint,allowed,actor):
        self._auth(actor,self.market.resolver)
        if self.status=="settled":
            raise Rejected("settled")
        integer(checkpoint,"checkpoint",minimum=0,maximum=len(self.support)-1)
        proposed=list(self.market.full_support)
        proposed[checkpoint]=frozenset(allowed)
        validate_support(self.market,tuple(proposed))
        if not proposed[checkpoint]:
            raise Rejected("empty report")
        self._reports[checkpoint]=proposed[checkpoint]
        self.status="paused"
        self.epoch+=1
        # No funding-support mutation, including contradictory reports.

    def resume(self,actor):
        self._auth(actor,self.market.resolver)
        if self.status!="paused":
            raise Rejected("not paused")
        self.status="open"
        self.epoch+=1

    def _narrowed(self,constraints):
        proposed=list(self.support)
        for t,allowed in constraints.items():
            integer(t,"checkpoint",minimum=0,maximum=len(proposed)-1)
            checked=list(self.market.full_support)
            checked[t]=frozenset(allowed)
            validate_support(self.market,tuple(checked))
            proposed[t]=proposed[t]&checked[t]
        support=tuple(proposed)
        work=extrema(self.market,Account(),self._covers,support).work  # nonempty path required
        resolved=dict(self._resolved)
        for cid,cover in self._covers.items():
            result=extrema(self.market,Account(holdings=((cid,1),)),{cid:cover},support)
            work+=result.work
            if work>self.market.limits.max_fact_work:
                raise Rejected("finalization work limit")
            if result.minimum==result.maximum:
                resolved[cid]=result.minimum
        return support,resolved

    def confirm(self,constraints,actor):
        """Harness finalizer supplies graph constraints, including finalization order."""
        self._auth(actor,self.market.resolver)
        if self.status=="settled" or self.market.finality!="progressive":
            raise Rejected("progressive finality unavailable")
        support,resolved=self._narrowed(constraints)
        if support==self.support:
            raise Rejected("no new final constraint")
        self._support,self._resolved=support,resolved
        self.epoch+=1
        # Remains paused if a report paused trading; reopen is explicit.

    def settle(self,constraints,actor):
        self._auth(actor,self.market.resolver)
        if self.status=="settled":
            raise Rejected("already settled")
        support,resolved=self._narrowed(constraints)
        if len(resolved)!=len(self._covers):
            raise Rejected("payoff-relevant observations unresolved")
        self._support,self._resolved=support,resolved
        self.status="settled"
        self.epoch+=1

    def claim(self,who,actor):
        self._auth(actor,who)
        if self.status!="settled" or who in self._claimed:
            raise Rejected("not claimable")
        old=self._account(who)
        account=self._materialized(old)
        if account.holdings or account.cash<0 or account.cash>self.escrow:
            raise Rejected("invalid settled account")
        amount=account.cash
        wallet=self.market.limits.checked(self._wallets[who]+amount)
        net=self.market.limits.checked(self._net[who]-amount)
        self._accounts[who]=Account(revision=old.revision+1)
        self._wallets[who]=wallet
        self._net[who]=net
        self.escrow-=amount
        self._claimed.add(who)
        self._receipts.append(("claim",who,amount,self.epoch))
        return amount

    def post_order(self,order,approval):
        if approval!=Approval(order.maker,order.digest):
            raise Rejected("maker approval missing")
        self._account(order.maker)
        if order.market!=self.market.identifier or order.epoch!=self.epoch:
            raise Rejected("wrong market or stale order")
        if self.status!="open" or self.now>=min(order.expires,self.market.close_at):
            raise Rejected("order expired or trading unavailable")
        if order.cover not in self._covers or order.cover in self._resolved:
            raise Rejected("unknown or resolved cover")
        if self.now>=self._covers[order.cover].trade_until:
            raise Rejected("cover trading closed")
        lim=self.market.limits
        lim.checked(order.quantity)
        lim.checked(order.unit_price*order.quantity)
        nonce=(order.maker,order.nonce)
        if nonce in self._order_nonces:
            raise Rejected("order nonce reused")
        self._orders[order.digest]=order
        self._filled[order.digest]=0
        self._order_nonces.add(nonce)
        return order.digest

    def cancel_order(self,order_id,actor):
        if order_id not in self._orders:
            raise Rejected("unknown order")
        self._auth(actor,self._orders[order_id].maker)
        self._cancelled.add(order_id)

    def fill(self,request,approval):
        if approval!=Approval(request.taker,request.digest):
            raise Rejected("taker approval missing")
        key="fill:"+request.digest
        if key in self._used or request.order in self._cancelled:
            raise Rejected("replayed fill or cancelled order")
        if request.order not in self._orders:
            raise Rejected("unknown order")
        order=self._orders[request.order]
        if request.taker==order.maker or request.epoch!=self.epoch or order.epoch!=self.epoch:
            raise Rejected("self fill or stale epoch")
        if request.quantity<order.min_fill or self._filled[request.order]+request.quantity>order.quantity:
            raise Rejected("fill size outside authorization")
        maker=self._account(order.maker)
        taker=self._account(request.taker)
        if request.revision!=taker.revision:
            raise Rejected("stale taker revision")
        qty=request.quantity*(1 if order.side=="sell" else -1)
        cash=self.market.limits.checked(order.unit_price*qty)
        batch=Batch(self.market.identifier,self.epoch,"fill:"+request.nonce,
                    min(request.expires,order.expires),(
                        Change(order.maker,maker.revision,((order.cover,-qty),),cash),
                        Change(request.taker,taker.revision,((order.cover,qty),),-cash,request.external)))
        prepared=self._candidate(batch)
        receipt=self._commit(batch,key,prepared)
        self._filled[request.order]+=request.quantity
        return receipt

    def profile_sale(self,seller,buyer,fraction,price,*,fee=0,recipient=None,
                     buyer_deposit=0,withdraw_proceeds=False,nonce):
        """Prepare, but do not authorize, an exact complete-profile transfer."""
        if seller==buyer or not isinstance(fraction,Fraction) or not 0<=fraction<=1:
            raise Rejected("invalid profile fraction or participants")
        integer(price,"price",minimum=0)
        integer(fee,"fee",minimum=0)
        integer(buyer_deposit,"deposit",minimum=0)
        account=self._materialized(self._account(seller))
        def scale(value):
            scaled=fraction*value
            if scaled.denominator!=1:
                raise Rejected("fraction not exactly representable")
            return self.market.limits.checked(scaled.numerator)
        lots=tuple((c,scale(q)) for c,q in account.holdings)
        cash=scale(account.cash)
        if withdraw_proceeds and price<fee:
            raise Rejected("proceeds do not cover fee")
        fees=() if not fee else (Fee(seller,recipient,fee),)
        return self.make_batch((
            Change(seller,self._account(seller).revision,tuple((c,-q) for c,q in lots),
                   price-cash,-(price-fee) if withdraw_proceeds else 0),
            Change(buyer,self._account(buyer).revision,lots,cash-price,buyer_deposit)),
            fees=fees,nonce=nonce)

    def audit(self,max_paths=100_000):
        """Independent full-path check, including wallets and escrow, for small cases."""
        from .oracle import paths, account_value
        if self.escrow<0 or any(v<0 for v in self._wallets.values()):
            raise AssertionError("negative token balance")
        if sum(self._wallets.values())+self.escrow!=self.endowment:
            raise AssertionError("wallet/escrow token conservation")
        count=0
        minima={who:None for who in self._accounts}
        for path in paths(self.market,self.support,max_paths):
            count+=1
            values={who:account_value(a,self._covers,path) for who,a in self._accounts.items()}
            if any(v<0 for v in values.values()) or sum(values.values())!=self.escrow:
                raise AssertionError(("entitlement conservation/funding",path,values,self.escrow))
            for who,value in values.items():
                minima[who]=value if minima[who] is None else min(minima[who],value)
        if not count:
            raise AssertionError("empty funding support")
        for who in self._accounts:
            if self.bounds(who).minimum!=minima[who]:
                raise AssertionError("verifier disagrees with exhaustive account evaluation")
        return count

    def snapshot(self):
        """Canonical complete mutable-state snapshot for rollback/replay tests."""
        return digest({
            "market":self.market.identifier,"covers":{k:asdict(v) for k,v in self._covers.items()},
            "accounts":{k:asdict(v) for k,v in self._accounts.items()},"wallets":self._wallets,
            "net":self._net,"support":[sorted(s) for s in self.support],"resolved":self._resolved,
            "reports":{k:sorted(v) for k,v in self._reports.items()},
            "orders":{k:asdict(v) for k,v in self._orders.items()},"filled":self._filled,
            "order_nonces":sorted(self._order_nonces),"cancelled":sorted(self._cancelled),
            "used":sorted(self._used),"claimed":sorted(self._claimed),"receipts":self._receipts,
            "epoch":self.epoch,"now":self.now,"escrow":self.escrow,
            "endowment":self.endowment,"status":self.status})
