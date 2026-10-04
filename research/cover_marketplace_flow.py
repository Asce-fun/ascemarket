"""Executable synthetic marketplace adapter over the unchanged v2 kernel.

Run: python3 -B research/cover_marketplace_flow.py
Template admission, route search and quote authorization here are research harnesses.
Approvals are NOT signatures, wallets are simulated, and quotes are assumptions.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model_v2.examples import checkpoint_market, checkpoint_cover, change, execute
from model_v2.ledger import Ledger, Fee, approve
from model_v2.schema import Rejected, integer
from model_v2.oracle import paths, cover_value, account_value


@dataclass(frozen=True)
class Quote:
    maker: str
    cover: str
    side: str
    price: int
    capacity: int
    epoch: int
    expires: int = 100


class Marketplace:
    """Restricted interval template + exact atomic related-cover routing.

    A production adapter must authenticate customer requests and every maker leg,
    atomically commit fill counters, enforce canonical terms, and own admission
    privileges safely. This class demonstrates none of those cryptographic controls.
    """
    def __init__(self):
        self.market, self.values = checkpoint_market(
            "interval-route-evidence", (tuple(range(8)),), lambda a, b: True)
        self.ledger = Ledger(self.market)
        self.templates = {}
        for owner in ("maker-T2", "maker-T5", "maker-T1", "user-1", "user-2", "router", "treasury"):
            self.ledger.register(owner, 1000)
        self.a = self.interval("maker-T2", 2, 8)
        self.b = self.interval("maker-T5", 5, 8)
        self.t = self.interval("maker-T1", 1, 8)
        execute(self.ledger, (change(self.ledger, "maker-T2", external=180),
                             change(self.ledger, "maker-T5", external=45),
                             change(self.ledger, "maker-T1", external=50)), "prefund")
        self.quotes = {
            "A-ask": Quote("maker-T2", self.a, "sell", 40, 3, 0),
            "B-bid": Quote("maker-T5", self.b, "buy", 15, 3, 0),
            "T-ask": Quote("maker-T1", self.t, "sell", 50, 1, 0),
            "A-bid": Quote("maker-T2", self.a, "buy", 38, 1, 0),
            "T-bid": Quote("maker-T1", self.t, "buy", 48, 1, 0),
            "B-ask": Quote("maker-T5", self.b, "sell", 16, 1, 0),
        }
        self.filled = {k: 0 for k in self.quotes}
        self.cancelled = set()
        self.sequence = 0

    def interval(self, creator, lo, hi, *, exception=0):
        if creator not in self.ledger.accounts:
            raise Rejected("unknown creator")
        integer(lo, "lower bound", minimum=0, maximum=7)
        integer(hi, "upper bound", minimum=1, maximum=8)
        integer(exception, "exception", minimum=0, maximum=100)
        if lo >= hi:
            raise Rejected("empty interval")
        key = (lo, hi, exception)
        if key not in self.templates:
            cover = checkpoint_cover(self.market, self.values,
                f"canonical interval [{lo},{hi}), cap 100, X={exception}", 1,
                lambda x: 100 if lo <= x < hi else 0, exception=exception)
            # Existing kernel admission is admin-only. This trusted research
            # adapter uses its harness admin; it does not change that requirement.
            self.templates[key] = self.ledger.admit(cover)
        return self.templates[key]

    def snapshot(self):
        return (self.ledger.snapshot(), tuple(sorted(self.filled.items())),
                tuple(sorted(self.cancelled)), self.sequence)

    def route(self, user, desired, legs, *, quantity=1, max_deposit=1000, min_withdrawal=0, preview=False):
        integer(quantity, "quantity", minimum=1)
        integer(max_deposit, "budget", minimum=0)
        integer(min_withdrawal, "minimum proceeds", minimum=0)
        if user not in ("user-1", "user-2"):
            raise Rejected("unknown customer")
        if len(set(legs)) != len(legs):
            raise Rejected("duplicate quote")
        # Desired customer change must be exactly replicated on EVERY permitted
        # full history, including cancellation, not just normal/current outcomes.
        residual = dict((cid, -q*quantity) for cid, q in desired)
        net_price = 0
        by_maker = {}
        for key in legs:
            q = self.quotes[key]
            if key in self.cancelled or self.filled[key]+quantity > q.capacity:
                raise Rejected("source liquidity unavailable")
            if q.epoch != self.ledger.epoch or self.ledger.now >= q.expires:
                raise Rejected("stale or expired source quote")
            sign = 1 if q.side == "sell" else -1
            residual[q.cover] = residual.get(q.cover, 0) + sign*quantity
            net_price += sign*q.price*quantity
            entry = by_maker.setdefault(q.maker, {"lots": {}, "cash": 0})
            entry["lots"][q.cover] = entry["lots"].get(q.cover, 0)-sign*quantity
            entry["cash"] += sign*q.price*quantity
        for p in paths(self.market):
            if sum(q*cover_value(self.ledger.covers[cid],p) for cid,q in residual.items()) != 0:
                raise Rejected("route payout mismatch, including exceptional outcomes")
        fee = quantity  # one synthetic currency unit per routed lot
        external = net_price+fee
        if external > max_deposit or max(-external,0) < min_withdrawal:
            raise Rejected("customer price limit")
        existing = dict(self.ledger.accounts[user].holdings)
        if any(q < 0 and existing.get(cid,0)+q*quantity < 0 for cid,q in desired):
            raise Rejected("customer does not own cover to change/close")
        changes = [change(self.ledger, user, tuple((c,q*quantity) for c,q in desired),
                          -net_price, external),
                   change(self.ledger, "router", tuple(residual.items()))]
        changes += [change(self.ledger, owner, tuple(d["lots"].items()),d["cash"])
                    for owner,d in by_maker.items()]
        batch = self.ledger.make_batch(changes, nonce=f"route-{self.sequence}",
                                       fees=(Fee(user,"treasury",fee),))
        result={"price": net_price, "fee": fee, "deposit": max(external,0),
                "withdrawal": max(-external,0), "legs":list(legs)}
        if preview:
            result["escrow"] = self.ledger.preview(batch)["escrow_after"]
            return result
        # Only a successful atomic kernel commit consumes quote quantity.
        self.ledger.execute(batch,[approve(batch,c.account) for c in batch.changes])
        for key in legs:
            self.filled[key] += quantity
        self.sequence += 1
        self.ledger.audit()
        return {**result, "escrow": self.ledger.escrow}

    def best_buy_quote(self, user, cover, **kwargs):
        """Bounded exact search: one ask or one ask less one bid.

        Funding/capacity are checked against the complete atomic package. This
        search is deliberately restricted; it is not a general integer optimizer.
        """
        asks=[k for k,q in self.quotes.items() if q.side=="sell"]
        bids=[k for k,q in self.quotes.items() if q.side=="buy"]
        candidates=[]
        for legs in [(a,) for a in asks]+[(a,b) for a in asks for b in bids]:
            try:
                candidates.append(self.route(user,((cover,1),),legs,preview=True,**kwargs))
            except Rejected:
                continue
        if not candidates:
            raise Rejected("no exact funded route within price limit")
        best=min(candidates,key=lambda q:(q["deposit"],len(q["legs"]),q["legs"]))
        return {**best,"eligible_routes":len(candidates)}

    def buy_best(self, user, cover, **kwargs):
        best=self.best_buy_quote(user,cover,**kwargs)
        return self.route(user,((cover,1),),tuple(best["legs"]),**kwargs)

    def buy(self, user, cover, **kwargs):
        return self.route(user, ((cover,1),), ("A-ask","B-bid"), **kwargs)

    def widen(self, user, old, new, **kwargs):
        return self.route(user, ((old,-1),(new,1)), ("T-ask","A-bid"), **kwargs)

    def close(self, user, cover, **kwargs):
        return self.route(user, ((cover,-1),), ("T-bid","B-ask"), **kwargs)


def reject_unchanged(marketplace, operation):
    before = marketplace.snapshot()
    try:
        operation()
    except Rejected as error:
        assert marketplace.snapshot() == before, "rejection mutated ledger/book"
        return str(error)
    raise AssertionError("invalid operation accepted")


def audit_all_accounts(m):
    l = m.ledger
    count = 0
    for path in paths(m.market):
        values = [account_value(a,l.covers,path) for a in l.accounts.values()]
        assert min(values) >= 0 and sum(values) == l.escrow
        assert account_value(l.accounts["router"],l.covers,path) == 0
        count += len(values)
    return count


def terminal_replays(m, cover):
    results = []
    for state in range(9):
        branch = deepcopy(m)
        l = branch.ledger
        before = dict(l.wallets)
        l.settle({1:{state}},"resolver")
        payouts = {who: l.claim(who,who) for who in l.accounts}
        # claim() returns the paid amount; compare against actual wallet movement too.
        for who, amount in payouts.items():
            assert l.wallets[who]-before[who] == amount
        assert payouts["user-2"] == (100 if 2 <= state < 5 else 0)
        assert payouts["router"] == 0 and payouts["user-1"] == 0
        l.audit()
        assert l.escrow == 0
        results.append({"outcome": state if state<8 else "cancellation", "payouts": payouts,
                        "user_2_net_pnl":l.wallets["user-2"]-1000,
                        "user_1_roundtrip_pnl":l.wallets["user-1"]-1000,
                        "final_escrow":l.escrow})
    return results


def capital_comparison():
    market, values=checkpoint_market("ctf-kernel-differential",((0,1,2),),lambda a,b:True)
    def fixture():
        l=Ledger(market)
        a=l.admit(checkpoint_cover(market,values,"A",1,lambda x:100 if x==0 else 0))
        b=l.admit(checkpoint_cover(market,values,"B",1,lambda x:100 if x==1 else 0))
        for who in ("maker","buyer-A","buyer-B"): l.register(who,1000)
        return l,a,b
    l,a,b=fixture()
    deposit=l.funding("maker",((a,-1),(b,-1)),cash=70)["deposit"]
    execute(l,(change(l,"maker",((a,-1),(b,-1)),70,deposit),
               change(l,"buyer-A",((a,1),),-30,30),
               change(l,"buyer-B",((b,1),),-40,40)),"atomic")
    assert deposit==30 and l.escrow==100
    terminal=[account_value(l.accounts["maker"],l.covers,p) for p in paths(market)]
    assert terminal==[0,0,100,100] # A, B, neither, cancellation: identical to CTF
    seq,a,b=fixture()
    first=seq.funding("maker",((a,-1),),cash=30)["deposit"]
    execute(seq,(change(seq,"maker",((a,-1),),30,first),
                 change(seq,"buyer-A",((a,1),),-30,30)),"first")
    execute(seq,(change(seq,"maker",((b,-1),),40),
                 change(seq,"buyer-B",((b,1),),-40,40)),"second")
    release=seq.bounds("maker").minimum
    execute(seq,(change(seq,"maker",external=-release),),"release")
    assert first==70 and release==40 and seq.net_deposits["maker"]==30
    return {"kernel_atomic_maker_peak":deposit,"kernel_sequential_maker_peak":first,
            "kernel_sequential_final_net_contribution":seq.net_deposits["maker"],
            "common_condition_CTF_atomic_maker_peak":30,"common_condition_CTF_sequential_maker_peak":70,
            "note":"CTF counterpart runs independently in run-evidence.cjs; matching claims have zero exceptional payouts."}


def maker_economics(terminals):
    # An assumed distribution compatible with all source bid/ask quotes.
    # Includes 1% cancellation. These are NOT estimated market probabilities.
    probabilities=[Fraction(x,1000) for x in (500,100,80,80,75,50,50,55,10)]
    assert sum(probabilities)==1
    expectations={}
    for who,deposit in (("maker-T2",180),("maker-T5",45),("maker-T1",50)):
        expectations[who]=sum(p*(row["payouts"][who]-deposit)
                              for p,row in zip(probabilities,terminals))
    assert expectations=={"maker-T2":Fraction(3),"maker-T5":Fraction(3,2),"maker-T1":Fraction(2)}
    fair={"T1":100*sum(probabilities[1:8]),"T2":100*sum(probabilities[2:8]),
          "T5":100*sum(probabilities[5:8]),"C":100*sum(probabilities[2:5])}
    assert fair=={"T1":Fraction(49),"T2":Fraction(39),"T5":Fraction(31,2),"C":Fraction(47,2)}
    # After this particular four-trade lifecycle, makers collectively received
    # 30 of net consideration and owe the remaining customer's 100-cap interval.
    # Gross EV = 30 - 100*p(interval). Changing beliefs is NOT a margin release.
    stress=[]
    for p in (Fraction(1,5),Fraction(47,200),Fraction(3,10),Fraction(3,8),Fraction(9,20)):
        for cost in (0,2,7):
            stress.append({"remaining_interval_probability":float(p),"total_assumed_maker_cost":cost,
                           "makers_expected_pnl":float(30-100*p-cost)})
    return {"probabilities_assumed_not_observed":[float(p) for p in probabilities],
            "fair_values_under_assumed_model":{k:float(v) for k,v in fair.items()},
            "makers_expected_gross_pnl":{k:float(v) for k,v in expectations.items()},
            "makers_total_expected_gross_pnl":6.5,"makers_combined_worst_terminal_pnl":-70,
            "break_even_remaining_interval_probability_before_costs":0.30,
            "stress_cases":stress,
            "interpretation":"Mechanically successful routing can lose money for makers. Under uniform normal outcomes it loses 7.5 before costs; under the quote-compatible assumed distribution it earns 6.5 before costs. Neither distribution is measured. Gas, capital carry, oracle delay, adverse selection and hedging remain unpriced here."}


def quote_search_experiment():
    m=Marketplace(); c=m.interval("user-1",2,5)
    m.ledger.register("direct-maker",1000)
    execute(m.ledger,(change(m.ledger,"direct-maker",external=67),),"direct-funding")
    m.quotes["C-direct-ask"]=Quote("direct-maker",c,"sell",33,2,0)
    m.filled["C-direct-ask"]=0
    before=m.snapshot()
    quote=m.best_buy_quote("user-1",c)
    assert m.snapshot()==before
    assert quote["price"]==25 and quote["eligible_routes"]==2
    assert quote["legs"]==["A-ask","B-bid"]
    # When a source quote disappears, the direct book is a legitimate fallback.
    fallback=deepcopy(m); fallback.cancelled.add("B-bid")
    fallback_quote=fallback.best_buy_quote("user-1",c)
    assert fallback_quote["price"]==33 and fallback_quote["legs"]==["C-direct-ask"]
    m.buy_best("user-1",c,max_deposit=26)
    assert m.filled["C-direct-ask"]==0
    # All 36 intervals are quoteable independently from one threshold book.
    # The 28 non-tail intervals have no own direct orders. This tests real route
    # search + funded execution, not merely mathematical payout equivalence.
    basis=Marketplace(); basis.quotes={}
    for k in range(8):
        cid=basis.interval("maker-T2",k,8)
        for side,spread in (("sell",2),("buy",-2)):
            basis.quotes[f"T{k}-{side}"]=Quote("maker-T2",cid,side,(8-k)*10+spread,10,0)
    basis.filled={k:0 for k in basis.quotes}
    executions=[]
    for lo in range(8):
        for hi in range(lo+1,9):
            branch=deepcopy(basis)
            cid=branch.interval("user-1",lo,hi)
            no_direct=all(q.cover!=cid for q in branch.quotes.values())
            result=branch.buy_best("user-1",cid)
            assert result["price"]==(hi-lo)*10+(2 if hi==8 else 4)
            audit_all_accounts(branch)
            for p in paths(branch.market):
                assert account_value(branch.ledger.accounts["user-1"],branch.ledger.covers,p)==(
                    100 if lo<=p[1]<hi else 0)
            executions.append({"interval":[lo,hi],"no_direct_orders":no_direct,**result})
    assert sum(row["no_direct_orders"] for row in executions)==28
    return {"cheaper_related_route_selected":quote,"direct_fallback_when_source_cancelled":fallback_quote,
            "executed_intervals":executions,"independent_funded_executions":36,
            "new_intervals_without_direct_orders":28,
            "boundary":"Each interval test starts from the same fresh maker inventory; this does not claim depth for all 36 simultaneous trades. Search considers at most two source legs, with integer lots and synthetic quotes."}


def main():
    m=Marketplace()
    admission_before=(m.ledger.escrow,dict(m.ledger.wallets))
    c=m.interval("user-1",2,5)
    assert m.interval("user-2",2,5)==c
    assert admission_before==(m.ledger.escrow,dict(m.ledger.wallets))
    assert all(q.cover!=c for q in m.quotes.values())
    failures={}
    failures["customer_budget"]=reject_unchanged(m,lambda:m.buy("user-1",c,max_deposit=25))
    failures["fractional_lot"]=reject_unchanged(m,lambda:m.buy("user-1",c,quantity=0.5))
    bad=m.interval("user-1",2,5,exception=60)
    failures["exception_mismatch"]=reject_unchanged(m,lambda:m.buy("user-1",bad))
    gone=deepcopy(m); gone.cancelled.add("B-bid")
    failures["cancelled_source"]=reject_unchanged(gone,lambda:gone.buy("user-1",c))
    stale=deepcopy(m); stale.ledger.post_report(1,{2},"resolver"); stale.ledger.resume("resolver")
    failures["stale_epoch"]=reject_unchanged(stale,lambda:stale.buy("user-1",c))
    late=deepcopy(m); late.ledger.advance(100)
    failures["expired_source"]=reject_unchanged(late,lambda:late.buy("user-1",c))
    empty=deepcopy(m)
    execute(empty.ledger,(change(empty.ledger,"maker-T5",external=-45),),"remove-source-funds")
    failures["underfunded_source"]=reject_unchanged(empty,lambda:empty.buy("user-1",c))
    # Separate the A leg from its B offset: router has a negative cash balance
    # and fails the kernel's pathwise funding test despite apparent price profit.
    def incomplete():
        execute(m.ledger,(change(m.ledger,"user-1",((c,1),),-25,26),
             change(m.ledger,"maker-T2",((m.a,-1),),40),
             change(m.ledger,"router",((m.a,1),(c,-1)),-15)),"incomplete",
             fees=(Fee("user-1","treasury",1),))
    failures["non_atomic_missing_offset"]=reject_unchanged(m,incomplete)
    stages=[]; path_account_checks=audit_all_accounts(m)
    stages.append({"action":"buy_new_cover_user_1",**m.buy("user-1",c,max_deposit=26)})
    path_account_checks+=audit_all_accounts(m)
    stages.append({"action":"buy_same_cover_user_2",**m.buy("user-2",c,max_deposit=26)})
    path_account_checks+=audit_all_accounts(m)
    failures["insufficient_quote_capacity"]=reject_unchanged(m,lambda:m.buy("user-2",c,quantity=2))
    d=m.interval("user-1",1,5)
    stages.append({"action":"widen_user_1_cover",**m.widen("user-1",c,d,max_deposit=13)})
    path_account_checks+=audit_all_accounts(m)
    failures["close_without_position"]=reject_unchanged(m,lambda:m.close("user-2",d))
    stages.append({"action":"close_user_1_cover",**m.close("user-1",d,min_withdrawal=31)})
    path_account_checks+=audit_all_accounts(m)
    assert m.ledger.wallets["user-1"]==992 and m.ledger.accounts["treasury"].cash==4
    assert m.ledger.escrow==309 and dict(m.ledger.accounts["user-2"].holdings)=={c:1}
    terminals=terminal_replays(m,c)
    result={"date":"2026-09-30","scope":"Synthetic executable routing over existing Python kernel; not a production matching engine or empirical demand/maker-profitability study.",
      "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      "model_sha256":{name:hashlib.sha256((ROOT/'model_v2'/name).read_bytes()).hexdigest()
                      for name in ('schema.py','verifier.py','oracle.py','ledger.py','examples.py')},
      "no_direct_created_cover_quotes":True,"same_template_fungible_across_creators":True,
      "cover_admission_without_issuance_or_new_funding":True,
      "stages":stages,"quote_fills":m.filled,"rejected_without_mutation":failures,
      "path_account_checks":path_account_checks,"terminal_scenarios":terminals,
      "capital_comparison":capital_comparison(),
      "maker_economics":maker_economics(terminals),
      "quote_search":quote_search_experiment(),
      "limitations":["Template adapter holds simulated admin privileges; current kernel is not permissionless cover admission.",
       "Quote approvals are harness assertions, not signatures; no persistent orderbook or external claim conversion.",
       "Exact replication requires compatible source, settlement domain, finality and exceptional payouts.",
       "Prices, maker balances and source availability are synthetic; no claim of commercially viable liquidity.",
       "This prototype is restricted to finite intervals; arbitrary path/scalar covers require separate treatment."]}
    output=Path(__file__).with_name('cover-marketplace-flow-results.json')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Passed: 4 lifecycle routes; 36 independently funded interval routes; {len(failures)} unchanged rejections; {path_account_checks} lifecycle account/path checks; 9 full settlements.')
    print(f'Results: {output}')


if __name__=='__main__': main()
