from dataclasses import replace
from fractions import Fraction
from itertools import product
import random
import unittest

from .schema import Account, Cover, Limits, Market, Rejected
from .ledger import Approval, Batch, Change, Fee, Fill, Ledger, Order, approve
from .verifier import extrema
from . import oracle
from .examples import (change, checkpoint_cover, checkpoint_market, change_cover,
                       exact_ramp, execute, football, price_market, rainfall, rainfall_replay,
                       deferred_history_market, deferred_cover)


class KernelTests(unittest.TestCase):
    def rejected_unchanged(self,ledger,operation):
        before=ledger.snapshot()
        with self.assertRaises(Rejected): operation()
        self.assertEqual(before,ledger.snapshot())
        ledger.audit()

    def simple(self,*,limits=Limits(),finality="progressive",exception=0):
        market,vals=checkpoint_market("binary",((0,1),),lambda a,b:True,limits=limits,finality=finality)
        l=Ledger(market)
        c=l.admit(checkpoint_cover(market,vals,"yes",1,lambda x:100*x,exception=exception))
        for who in ("maker","buyer","other","treasury"):l.register(who,10000)
        return l,c

    def open_simple(self,l,c,quantity=1):
        return execute(l,(change(l,"maker",((c,-quantity),),40*quantity,60*quantity),
                          change(l,"buyer",((c,quantity),),-40*quantity,40*quantity)),"open")

    def test_rainfall_full_lifecycle(self):
        r=rainfall_replay()
        self.assertEqual(r["maker_deposit"],20)
        self.assertEqual([s["withdrawable"]["buyer_a"] for s in r["stages"][:3]],[0,0,100])
        self.assertEqual(r["stages"][-1]["escrow"],0)
        self.assertEqual(r["buyer_a_profit"],70)
        self.assertEqual(r["maker_profit"],-20)

    def test_cancellation_before_confirmation_pays_zero(self):
        l,vals,a,b=rainfall()
        l.settle({1:{len(vals[0])}},"resolver")
        self.assertEqual(l.claim("buyer_a","buyer_a"),0)
        self.assertEqual(l.claim("buyer_b","buyer_b"),0)
        self.assertEqual(l.claim("maker","maker"),100)
        l.claim("treasury","treasury")
        l.audit()
        self.assertEqual(l.escrow,0)

    def test_cancellation_after_confirmation_preserves_claim(self):
        l,vals,a,b=rainfall()
        l.confirm({1:{2}},"resolver")
        l.settle({2:{len(vals[1])}},"resolver")
        self.assertEqual(l.claim("buyer_a","buyer_a"),100)
        l.audit()

    def test_exception_can_destroy_normal_offset(self):
        market,vals=checkpoint_market("void",((0,1),),lambda a,b:True)
        a=checkpoint_cover(market,vals,"a",1,lambda x:100*x,exception=100)
        b=checkpoint_cover(market,vals,"b",1,lambda x:100*(1-x),exception=100)
        covers={x.identifier:x for x in (a,b)}
        result=extrema(market,Account(holdings=tuple((cid,-1) for cid in covers)),covers)
        self.assertEqual(result.minimum,-200)
        self.assertEqual(result.witness[-1],2)

    def test_football_netting_and_window_payment(self):
        l,vals,h,k=football()
        self.assertEqual(l.net_deposits["maker"],40)
        l.audit()
        l.confirm({2:{1}},"resolver") # 1-1 at window end
        self.assertEqual(l.bounds("h_buyer").minimum,100)
        self.assertEqual(l.bounds("k_buyer").maximum,0)
        l.audit()

    def test_free_price_no_cross_time_offset(self):
        l,vals,a,b=price_market()
        l.register("maker",1000)
        self.assertEqual(l.funding("maker",((a,-1),(b,-1)))["deposit"],200)
        c=l.admit(checkpoint_cover(l.market,vals,"other range same checkpoint",1,lambda x:100 if x==3200 else 0))
        self.assertEqual(l.funding("maker",((a,-1),(c,-1)))["deposit"],100)

    def test_provisional_report_never_changes_funding(self):
        l,c=self.simple()
        support=l.support
        l.post_report(1,{0},"resolver")
        l.resume("resolver")
        l.post_report(1,{1},"resolver")
        self.assertEqual(l.support,support)
        l.resume("resolver")
        batch=l.make_batch((change(l,"maker",((c,-2),),100),change(l,"buyer",((c,2),),-100,100)),nonce="unsafe")
        self.rejected_unchanged(l,lambda:l.execute(batch,[approve(batch,c.account) for c in batch.changes]))

    def test_end_finality_blocks_intermediate_release(self):
        l,c=self.simple(finality="end")
        self.open_simple(l,c)
        l.post_report(1,{1},"resolver")
        self.assertEqual(l.bounds("buyer").minimum,0)
        self.rejected_unchanged(l,lambda:l.confirm({1:{1}},"resolver"))
        l.settle({1:{1}},"resolver")
        self.assertEqual(l.claim("buyer","buyer"),100)
        l.audit()

    def test_conflicting_final_fact_is_atomic(self):
        l,c=self.simple()
        self.open_simple(l,c)
        l.confirm({1:{1}},"resolver")
        self.rejected_unchanged(l,lambda:l.confirm({1:{0}},"resolver"))

    def test_empty_support_and_unknown_states_rejected(self):
        l,c=self.simple()
        for states in (set(),{999},{True}):
            self.rejected_unchanged(l,lambda states=states:l.confirm({1:states},"resolver"))

    def test_out_of_order_fact_retains_earlier_payout(self):
        l,vals,a,b=rainfall()
        l.confirm({2:{2}},"resolver")
        self.assertEqual(l.bounds("buyer_a").minimum,0)
        self.assertEqual(l.bounds("buyer_a").maximum,100)
        self.rejected_unchanged(l,lambda:l.settle({},"resolver"))
        l.confirm({1:{2}},"resolver")
        l.settle({},"resolver")
        self.assertEqual(l.claim("buyer_a","buyer_a"),100)
        l.audit()

    def test_finalization_does_not_duplicate_lazy_credit(self):
        l,vals,a,b=rainfall()
        l.confirm({1:{2}},"resolver")
        expected=l.bounds("buyer_a")
        l.materialize("buyer_a","buyer_a")
        snapshot=l.snapshot()
        l.materialize("buyer_a","buyer_a")
        self.assertEqual(snapshot,l.snapshot())
        self.assertEqual(l.bounds("buyer_a").minimum,expected.minimum)
        l.audit() # other holders are still lazy
        for who in l.accounts:l.materialize(who,who)
        l.audit()

    def test_deleting_one_tail_does_not_always_release_cash(self):
        market=Market("tails",(("low","middle","high"),),())
        cover=Cover(market.identifier,"middle",((0,1,100),))
        a=Account(holdings=((cover.identifier,1),))
        covers={cover.identifier:cover}
        self.assertEqual(extrema(market,a,covers).minimum,0)
        self.assertEqual(extrema(market,a,covers,(frozenset({1,2}),)).minimum,0)

    def test_unauthorized_roles(self):
        l,c=self.simple()
        self.rejected_unchanged(l,lambda:l.confirm({1:{1}},"attacker"))
        self.rejected_unchanged(l,lambda:l.post_report(1,{1},"attacker"))
        self.rejected_unchanged(l,lambda:l.materialize("buyer","attacker"))

    def test_batch_requires_all_approvals_and_exact_payload(self):
        l,c=self.simple()
        b=l.make_batch((change(l,"buyer",external=10),),nonce="a")
        self.rejected_unchanged(l,lambda:l.execute(b,[]))
        other=replace(b,nonce="b")
        self.rejected_unchanged(l,lambda:l.execute(other,[approve(b,"buyer")]))

    def test_batch_conservation_wallet_and_stale_revision(self):
        l,c=self.simple()
        invalid=[(change(l,"buyer",((c,1),),external=100),),
                 (change(l,"buyer",cash=1),),
                 (change(l,"buyer",external=10001),),
                 (Change("buyer",99,external=1),)]
        for i,changes in enumerate(invalid):
            b=l.make_batch(changes,nonce=str(i))
            self.rejected_unchanged(l,lambda b=b:l.execute(b,[approve(b,c.account) for c in b.changes]))

    def test_replay_and_expiry(self):
        l,c=self.simple()
        b=execute(l,(change(l,"buyer",external=100),),"deposit")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,"buyer")]))
        b=l.make_batch((change(l,"buyer",external=1),),nonce="expired",expires=10)
        l.advance(10)
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,"buyer")]))

    def test_market_and_epoch_domain_separation(self):
        l,c=self.simple()
        b=l.make_batch((change(l,"buyer",external=1),),nonce="epoch")
        l.post_report(1,{1},"resolver")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,"buyer")]))
        b=replace(b,market="other",epoch=l.epoch)
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,"buyer")]))

    def test_fee_recipient_and_atomic_fee_failure(self):
        l,c=self.simple()
        b=l.make_batch((change(l,"buyer",external=10),),fees=(Fee("buyer","treasury",3),),nonce="fee")
        l.execute(b,[approve(b,"buyer")])
        self.assertEqual(l.bounds("buyer").minimum,7)
        self.assertEqual(l.bounds("treasury").minimum,3)
        l.audit()
        b=l.make_batch((change(l,"buyer"),),fees=(Fee("buyer","treasury",8),),nonce="too-much")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,"buyer")]))

    def test_failed_batch_with_resolved_holdings_does_not_materialize(self):
        l,vals,a,b=rainfall()
        l.confirm({1:{2}},"resolver")
        batch=l.make_batch((change(l,"buyer_a",external=-101),),nonce="fail")
        self.rejected_unchanged(l,lambda:l.execute(batch,[approve(batch,"buyer_a")]))
        self.assertTrue(l.accounts["buyer_a"].holdings)

    def test_selected_leg_exit_removes_offset_and_needs_funding(self):
        l,vals,a,b=rainfall()
        # Close A at 90: maker loses the premium-funded offset.
        self.assertEqual(l.funding("maker",((a,1),),cash=-90)["deposit"],90)
        batch=l.make_batch((change(l,"maker",((a,1),),-90),change(l,"buyer_a",((a,-1),),90)),nonce="close")
        self.rejected_unchanged(l,lambda:l.execute(batch,[approve(batch,c.account) for c in batch.changes]))

    def negative_cash(self):
        # Two lots pay 100/200, including exception=100; floor can be withdrawn.
        market,vals=checkpoint_market("signedcash",((0,1),),lambda a,b:True)
        l=Ledger(market)
        c=l.admit(checkpoint_cover(market,vals,"positivefloor",1,lambda x:50+50*x,exception=50))
        for who in ("maker","buyer","other","treasury"):l.register(who,1000)
        execute(l,(change(l,"maker",((c,-2),),100,100),change(l,"buyer",((c,2),),-100,100)),"open")
        execute(l,(change(l,"buyer",external=-100),),"withdraw-floor")
        self.assertEqual(l.accounts["buyer"].cash,-100)
        return l,c

    def test_holdings_only_fraction_can_be_insolvent(self):
        l,c=self.negative_cash()
        b=l.make_batch((change(l,"buyer",((c,-1),),25),change(l,"other",((c,1),),-25,25)),nonce="bad-half")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,c.account) for c in b.changes]))

    def test_complete_profile_half_includes_negative_cash(self):
        l,c=self.negative_cash()
        b=l.profile_sale("buyer","other",Fraction(1,2),25,buyer_deposit=25,withdraw_proceeds=True,nonce="half")
        l.execute(b,[approve(b,c.account) for c in b.changes])
        self.assertEqual(l.accounts["buyer"].cash,-50)
        self.assertEqual(l.bounds("buyer").minimum,0)
        self.assertEqual(l.bounds("buyer").maximum,50)
        l.audit()

    def test_fraction_and_cash_must_be_exactly_representable(self):
        l,c=self.negative_cash()
        self.rejected_unchanged(l,lambda:l.profile_sale("buyer","other",Fraction(1,3),25,nonce="third"))
        self.rejected_unchanged(l,lambda:l.profile_sale("buyer","other",0.5,25,nonce="float"))

    def test_full_profile_sale_fee_and_buyer_check(self):
        l,c=self.negative_cash()
        b=l.profile_sale("buyer","other",Fraction(1),30,fee=5,recipient="treasury",
                         buyer_deposit=30,withdraw_proceeds=True,nonce="whole")
        l.execute(b,[approve(b,c.account) for c in b.changes])
        self.assertEqual(l.bounds("buyer").maximum,0)
        self.assertEqual(l.bounds("treasury").minimum,5)
        l.audit()

    def test_duplicate_claim_and_prior_withdrawal(self):
        l,c=self.simple()
        self.open_simple(l,c)
        l.confirm({1:{1}},"resolver")
        execute(l,(change(l,"buyer",external=-60),),"withdraw")
        l.settle({},"resolver")
        self.assertEqual(l.claim("buyer","buyer"),40)
        self.rejected_unchanged(l,lambda:l.claim("buyer","buyer"))
        for who in ("maker","other","treasury"):l.claim(who,who)
        self.assertEqual(l.escrow,0)
        l.audit()

    def test_resolved_cover_cannot_trade_or_be_issued(self):
        l,c=self.simple()
        self.open_simple(l,c)
        l.confirm({1:{1}},"resolver")
        b=l.make_batch((change(l,"maker",((c,1),),-100),change(l,"buyer",((c,-1),),100)),nonce="late")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,c.account) for c in b.changes]))
        new=replace(l.covers[c],label="same resolved exposure")
        self.rejected_unchanged(l,lambda:l.admit(new))

    def test_integer_and_ramp_validation(self):
        for value in (1.0,True,Fraction(1,2)):
            with self.assertRaises(Rejected):Account(cash=value)
        self.assertEqual(exact_ramp(1,0,3,300),100)
        with self.assertRaises(Rejected):exact_ramp(1,0,3,1)
        with self.assertRaises(Rejected):exact_ramp(1,3,0,1)

    def test_cover_and_graph_validation(self):
        l,c=self.simple()
        for bad in (replace(l.covers[c],market="other"),
                    Cover(l.market.identifier,"bad",((50,0,10),)),
                    Cover(l.market.identifier,"bad-edge",edges=((0,0,99,1),))):
            self.rejected_unchanged(l,lambda bad=bad:l.admit(bad))
        with self.assertRaises(Rejected):Cover("x","dup",((0,0,1),(0,0,2)))
        with self.assertRaises(Rejected):Market("empty",(("a",),("b",)),((),))
        with self.assertRaises(Rejected):Market("bool",(("a",),("b",)),(((True,0),),))

    def test_factor_canonicalization_and_readonly_state(self):
        l,c=self.simple()
        first=Cover(l.market.identifier,"same",((1,1,100),(1,0,0)))
        second=Cover(l.market.identifier,"same",((1,1,100),))
        self.assertEqual(first.identifier,second.identifier)
        with self.assertRaises(TypeError):l.accounts["buyer"]=Account(cash=999)
        with self.assertRaises(TypeError):l.covers[c]=second

    def test_intermediate_arithmetic_overflow(self):
        market=Market("overflow",(("a","b"),),(),limits=Limits(max_abs=100))
        c=Cover(market.identifier,"c",((0,0,60),))
        with self.assertRaises(Rejected):extrema(market,Account(holdings=((c.identifier,2),)),{c.identifier:c})

    def test_combined_complexity_limit(self):
        l,c=self.simple(limits=Limits(max_holdings=1))
        other=l.admit(replace(l.covers[c],label="other"))
        b=l.make_batch((change(l,"maker",((c,-1),(other,-1)),80,120),
                        change(l,"buyer",((c,1),(other,1)),-80,80)),nonce="too-complex")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,c.account) for c in b.changes]))

    def test_batch_work_budget(self):
        l,c=self.simple(limits=Limits(max_batch_work=1))
        b=l.make_batch((change(l,"buyer",external=1),),nonce="work")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,"buyer")]))

    def test_pause_allows_funded_withdrawal_not_trading(self):
        l,c=self.simple()
        execute(l,(change(l,"buyer",external=100),),"deposit")
        l.post_report(1,{1},"resolver")
        execute(l,(change(l,"buyer",external=-20),),"withdraw")
        b=l.make_batch((change(l,"buyer",cash=-1),change(l,"other",cash=1)),nonce="paused")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,c.account) for c in b.changes]))

    def test_standing_orders_recheck_capacity_without_revision_lock(self):
        l,c=self.simple()
        execute(l,(change(l,"maker",external=60),),"backing")
        order=Order(l.market.identifier,"maker",c,"sell",3,40,1,100,l.epoch,"o")
        oid=l.post_order(order,approve(order,"maker"))
        f=Fill(oid,"buyer",0,1,40,l.epoch,"f",100)
        l.fill(f,approve(f,"buyer"))
        l.audit()
        f2=Fill(oid,"other",0,1,40,l.epoch,"f2",100)
        self.rejected_unchanged(l,lambda:l.fill(f2,approve(f2,"other")))
        execute(l,(change(l,"maker",external=60),),"more-backing")
        l.fill(f2,approve(f2,"other"))
        l.audit()
        self.assertEqual(l._filled[oid],2)

    def test_order_cancellation_replay_and_overfill(self):
        l,c=self.simple()
        execute(l,(change(l,"maker",external=1000),),"backing")
        o=Order(l.market.identifier,"maker",c,"sell",1,40,1,100,l.epoch,"o")
        oid=l.post_order(o,approve(o,"maker"))
        f=Fill(oid,"buyer",0,1,40,l.epoch,"f",100)
        l.fill(f,approve(f,"buyer"))
        self.rejected_unchanged(l,lambda:l.fill(f,approve(f,"buyer")))
        f2=replace(f,taker="other",nonce="f2")
        self.rejected_unchanged(l,lambda:l.fill(f2,approve(f2,"other")))
        self.rejected_unchanged(l,lambda:l.post_order(o,approve(o,"maker")))
        o2=replace(o,nonce="new")
        oid2=l.post_order(o2,approve(o2,"maker"))
        self.rejected_unchanged(l,lambda:l.cancel_order(oid2,"attacker"))
        l.cancel_order(oid2,"maker")
        f3=replace(f2,order=oid2)
        self.rejected_unchanged(l,lambda:l.fill(f3,approve(f3,"other")))

    def test_order_buy_side_and_epoch_refresh(self):
        l,c=self.simple()
        execute(l,(change(l,"maker",external=40),),"backing")
        o=Order(l.market.identifier,"maker",c,"buy",1,40,1,100,l.epoch,"buy")
        oid=l.post_order(o,approve(o,"maker"))
        f=Fill(oid,"buyer",0,1,60,l.epoch,"f",100)
        l.fill(f,approve(f,"buyer"))
        l.audit()
        self.assertEqual(dict(l.accounts["maker"].holdings)[c],1)
        o2=replace(o,nonce="next")
        oid2=l.post_order(o2,approve(o2,"maker"))
        l.post_report(1,{1},"resolver")
        l.resume("resolver")
        f2=Fill(oid2,"other",0,1,60,l.epoch,"f2",100)
        self.rejected_unchanged(l,lambda:l.fill(f2,approve(f2,"other")))

    def test_order_approvals_and_minimum_fill(self):
        l,c=self.simple()
        execute(l,(change(l,"maker",external=1000),),"backing")
        o=Order(l.market.identifier,"maker",c,"sell",4,40,2,100,l.epoch,"o")
        self.rejected_unchanged(l,lambda:l.post_order(o,Approval("other",o.digest)))
        oid=l.post_order(o,approve(o,"maker"))
        f=Fill(oid,"buyer",0,1,40,l.epoch,"f",100)
        self.rejected_unchanged(l,lambda:l.fill(f,approve(f,"buyer")))
        f=replace(f,quantity=2,external=80)
        self.rejected_unchanged(l,lambda:l.fill(f,Approval("other",f.digest)))
        l.fill(f,approve(f,"buyer"))
        l.audit()

    def test_equivalent_baskets_same_funding(self):
        l,c=self.simple()
        double=replace(l.covers[c],label="double",nodes=tuple((t,v,a*2) for t,v,a in l.covers[c].nodes))
        d=l.admit(double)
        self.assertEqual(l.funding("maker",((c,-2),))["deposit"],l.funding("maker",((d,-1),))["deposit"])

    def test_unreachable_negative_state_does_not_poison_minimum(self):
        m=Market("disconnected",(("start",),("reachable","dead")),(((0,0),),))
        c=Cover(m.identifier,"dead factor",((1,1,-100),))
        result=extrema(m,Account(holdings=((c.identifier,1),)),{c.identifier:c})
        self.assertEqual(result.minimum,0)
        self.assertEqual(result.witness,(0,0))

    def test_next_scorer_requires_augmented_state(self):
        # Same final score, different retained first-scorer label.
        m=Market("event-order",(("0-0",),("1-1 home first","1-1 away first")),(((0,0),(0,1)),))
        c=Cover(m.identifier,"home next",((1,0,100),))
        result=extrema(m,Account(holdings=((c.identifier,1),)),{c.identifier:c})
        self.assertEqual((result.minimum,result.maximum),(0,100))
        self.assertEqual(len({min(x,7) for x in (7,8)}),1) # lossy score bucket cannot encode winner

    def test_suffix_optimization_with_holes_and_signed_holdings(self):
        r=random.Random(437)
        for case in range(250):
            m,values=checkpoint_market(str(case),(tuple(range(5)),)*4,
                (lambda a,b:a<=b) if case%2 else (lambda a,b:True))
            covers={}
            for t in range(1,5):
                table=[r.randrange(-20,21) for _ in range(5)]
                c=checkpoint_cover(m,values,str(t),t,lambda x:table[x])
                covers[c.identifier]=c
            a=Account(r.randrange(-30,31),tuple((c,r.randrange(-3,4)) for c in covers))
            support=(frozenset({0}),)+tuple(frozenset(v for v in range(6) if v==5 or r.random()<.6) for _ in range(4))
            fast=extrema(m,a,covers,support)
            generic=extrema(m,a,covers,support,optimized=False)
            exhaustive=oracle.extrema(m,a,covers,support)
            self.assertEqual((fast.minimum,fast.maximum),(generic.minimum,generic.maximum))
            self.assertEqual((fast.minimum,fast.maximum),exhaustive[:2])
            self.assertEqual(oracle.account_value(a,covers,fast.witness),fast.minimum)

    def test_randomized_ledger_lifecycles(self):
        from .research import randomized_replay
        for seed in range(20):
            result=randomized_replay(seed,30)
            self.assertEqual(result["final_escrow"],0)

    def test_resolved_values_cannot_create_arithmetic_trap(self):
        # Opposing large terms cancel economically, but individual materialization
        # must also fit the deployment's signed arithmetic envelope.
        m=Market("budget",(("a","b"),),(),limits=Limits(max_abs=100))
        a=Cover(m.identifier,"a",((0,0,60),(0,1,50)))
        b=Cover(m.identifier,"b",((0,0,-60),(0,1,-50)))
        with self.assertRaises(Rejected):
            extrema(m,Account(holdings=((a.identifier,1),(b.identifier,1))),{a.identifier:a,b.identifier:b})

    def test_portable_fixture_file(self):
        import json
        from pathlib import Path
        fixtures=json.loads(Path(__file__).with_name("fixtures.json").read_text())
        for case in fixtures["cases"]:
            data=dict(case["market"])
            data["limits"]=Limits(**data["limits"])
            market=Market(**data)
            covers={}
            for row in case["covers"]:
                cover=Cover(**row)
                cover.validate(market)
                covers[cover.identifier]=cover
            account=Account(**case["account"])
            support=tuple(frozenset(layer) for layer in case["support"])
            actual=extrema(market,account,covers,support)
            exhaustive=oracle.extrema(market,account,covers,support)
            expected=case["expected"]
            self.assertEqual((actual.minimum,actual.maximum),(expected["minimum"],expected["maximum"]),case["name"])
            self.assertEqual(exhaustive[:2],(expected["minimum"],expected["maximum"]),case["name"])

    def test_foreign_cover_and_unknown_account_changes_rejected(self):
        l,c=self.simple()
        b=l.make_batch((change(l,"buyer",(("unknown",1),)),change(l,"maker",(("unknown",-1),))),nonce="unknown")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,c.account) for c in b.changes]))
        b=l.make_batch((Change("unknown",0,external=1),),nonce="account")
        self.rejected_unchanged(l,lambda:l.execute(b,[approve(b,"unknown")]))

    def test_market_close_stops_orders_but_allows_safe_withdrawal(self):
        l,c=self.simple()
        execute(l,(change(l,"buyer",external=100),),"fund")
        l.advance(l.market.close_at)
        o=Order(l.market.identifier,"maker",c,"sell",1,40,1,l.now+100,l.epoch,"late")
        self.rejected_unchanged(l,lambda:l.post_order(o,approve(o,"maker")))
        execute(l,(change(l,"buyer",external=-100),),"withdraw-at-close")
        l.audit()

    def test_incompatible_late_cover_does_not_change_existing_positions(self):
        l,c=self.simple()
        self.open_simple(l,c)
        before={p:oracle.account_value(l.accounts["buyer"],l.covers,p) for p in oracle.paths(l.market)}
        additional=replace(l.covers[c],label="new public listing")
        l.admit(additional)
        after={p:oracle.account_value(l.accounts["buyer"],l.covers,p) for p in oracle.paths(l.market)}
        self.assertEqual(before,after)
        foreign=replace(additional,market="new state schema")
        self.rejected_unchanged(l,lambda:l.admit(foreign))

    def test_end_finality_cancellation_does_not_keep_provisional_winnings(self):
        m,histories=deferred_history_market("deferred",((0,1),(0,1)),lambda a,b:a<=b)
        l=Ledger(m)
        c=l.admit(deferred_cover(m,histories,"early-high",lambda h:100 if h[0]==1 else 0))
        for who in ("maker","buyer"):l.register(who,1000)
        execute(l,(change(l,"maker",((c,-1),),40,60),change(l,"buyer",((c,1),),-40,40)),"open")
        l.post_report(1,{1},"resolver")
        self.assertEqual(l.bounds("buyer").minimum,0)
        l.settle({2:{len(histories[-1])}},"resolver")
        self.assertEqual(l.claim("buyer","buyer"),0)
        self.assertEqual(l.claim("maker","maker"),100)
        l.audit()

    def test_augmented_state_can_encode_nonadjacent_condition(self):
        m,hs=deferred_history_market("path",((0,1),)*3,lambda a,b:True)
        c=deferred_cover(m,hs,"return after move",lambda h:100 if h[0]==h[2] and h[0]!=h[1] else 0)
        c.validate(m)
        a=Account(holdings=((c.identifier,1),))
        result=extrema(m,a,{c.identifier:c})
        brute=oracle.extrema(m,a,{c.identifier:c})
        self.assertEqual((result.minimum,result.maximum),(0,100))
        self.assertEqual(brute[:2],(0,100))

    def test_history_augmentation_refuses_excessive_state_space(self):
        with self.assertRaises(Rejected):
            deferred_history_market("too-big",(tuple(range(10)),)*6,lambda a,b:True,limits=Limits(max_states=100))
        with self.assertRaises(Rejected):
            checkpoint_market("wrong-builder",((0,1),)*2,lambda a,b:True,finality="end")

    def test_admission_reserves_budget_for_future_finalization(self):
        m,values=checkpoint_market("budget",((0,1),),lambda a,b:True,limits=Limits(max_fact_work=1))
        l=Ledger(m)
        c=checkpoint_cover(m,values,"yes",1,lambda x:100*x)
        self.rejected_unchanged(l,lambda:l.admit(c))

    def test_sparse_suffix_does_not_exceed_reserved_work(self):
        m=Market("sparse-suffix",(("start",),tuple(str(i) for i in range(100))),(((0,99),),))
        result=extrema(m,Account(),{})
        self.assertLessEqual(result.work,m.work)
        self.assertEqual(result.minimum,0)

    def test_random_general_graph_differential(self):
        r=random.Random(982451653)
        for case in range(1000):
            sizes=[r.randint(1,4) for _ in range(r.randint(1,5))]
            layers=tuple(tuple(str(v) for v in range(n)) for n in sizes)
            edges=tuple(tuple((v,w) for v in range(sizes[t]) for w in range(sizes[t+1])
                              if (v,w)==(0,0) or r.random()<.55) for t in range(len(sizes)-1))
            m=Market(str(case),layers,edges)
            covers={}
            for j in range(r.randint(1,5)):
                c=Cover(m.identifier,str(j),
                        tuple((t,v,r.randint(-20,20)) for t,n in enumerate(sizes) for v in range(n)),
                        tuple((t,v,w,r.randint(-20,20)) for t,es in enumerate(edges) for v,w in es))
                c.validate(m)
                covers[c.identifier]=c
            account=Account(r.randint(-100,100),tuple((c,r.randint(-4,4)) for c in covers))
            support=tuple(frozenset(v for v in range(n) if v==0 or r.random()<.6) for n in sizes)
            fast=extrema(m,account,covers,support)
            slow=oracle.extrema(m,account,covers,support)
            self.assertEqual((fast.minimum,fast.maximum),slow[:2],case)
            self.assertEqual(oracle.account_value(account,covers,fast.witness),fast.minimum)
            # A further nonempty restriction cannot reduce the account minimum.
            restricted=tuple(frozenset({v}) for v in fast.witness)
            self.assertGreaterEqual(extrema(m,account,covers,restricted).minimum,fast.minimum)


if __name__ == "__main__":
    unittest.main()
