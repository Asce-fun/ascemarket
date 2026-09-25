"""Deterministic adversarial accounting replays and verifier benchmarks.

This is synthetic kernel backtesting, NOT historical pricing/P&L validation.
Run: python3 -B -m model_v2.research --output model_v2/results.json
"""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict, replace
from fractions import Fraction
import json
from pathlib import Path
import platform
import random
import statistics
import time

from .schema import Account, Cover, Market, Rejected
from .ledger import Change, Fee, Fill, Ledger, Order, approve
from .verifier import extrema
from . import oracle
from .examples import (change, checkpoint_cover, checkpoint_market, change_cover,
                       execute, rainfall_replay, football, price_market)


def randomized_replay(seed,steps=60):
    r=random.Random(seed)
    market,values=checkpoint_market(f"random-{seed}",(tuple(range(4)),)*3,lambda a,b:a<=b)
    l=Ledger(market)
    ids=[]
    for t in range(1,4):
        ids.append(l.admit(checkpoint_cover(market,values,f"high-{t}",t,lambda x:20 if x>=2 else 0)))
        ids.append(l.admit(checkpoint_cover(market,values,f"low-{t}",t,lambda x:20 if x<2 else 0)))
    ids.append(l.admit(change_cover(market,values,"increment",1,lambda a,b:10*(b-a))))
    eventual_path=r.choice(list(oracle.paths(market)))
    users=("a","b","c")
    for who in (*users,"treasury"):l.register(who,1_000_000)
    accepted=rejected=audited_paths=skipped=0
    rejection_reasons={}
    peak=0
    for step in range(steps):
        before=l.snapshot()
        try:
            action=r.randrange(10)
            who,other=r.sample(users,2)
            if action<6:
                cid=r.choice(ids)
                if cid in l.resolved:
                    skipped+=1
                    continue
                qty=r.choice((-3,-2,-1,1,2,3))
                price=r.randrange(0,31)*abs(qty)
                cash=-price if qty>0 else price
                fee=r.randrange(0,3)
                d1=l.funding(who,((cid,qty),),cash,fee)["deposit"]
                d2=l.funding(other,((cid,-qty),),-cash)["deposit"]
                # Some deliberate underfunding; some incorrect signatures.
                if action==0:d1=max(0,d1-1)
                batch=l.make_batch((change(l,who,((cid,qty),),cash,d1),
                                    change(l,other,((cid,-qty),),-cash,d2)),
                                   fees=(Fee(who,"treasury",fee),),nonce=f"{seed}-{step}")
                approvals=[approve(batch,c.account) for c in batch.changes]
                if action==1:approvals=approvals[:1]
                l.execute(batch,approvals)
            elif action==6:
                floor=l.bounds(who).minimum
                amount=floor if r.random()<.7 else floor+1
                execute(l,(change(l,who,external=-amount),),f"withdraw-{step}")
            elif action==7:
                # Report and correction invalidate quotes but never collateral.
                old=l.support
                t=r.randrange(1,4)
                l.post_report(t,{r.randrange(4)},"resolver")
                l.resume("resolver")
                assert l.support==old
                if step>steps//3 and r.random()<.35 and l.support[t]!=frozenset({eventual_path[t]}):
                    prior={u:l.bounds(u).minimum for u in l.accounts}
                    l.confirm({t:{eventual_path[t]}},"resolver")
                    assert all(l.bounds(u).minimum>=prior[u] for u in l.accounts)
            elif action==8:
                l.materialize(who,who)
            else:
                # Whole-profile sale; enough buyer funding based on exact change.
                price=r.randrange(0,30)
                batch=l.profile_sale(who,other,Fraction(1),price,nonce=f"sale-{step}")
                buyer=batch.changes[1]
                dep=l.funding(other,buyer.holdings,buyer.cash)["deposit"]
                batch=replace(batch,changes=(batch.changes[0],replace(buyer,external=dep)))
                l.execute(batch,[approve(batch,c.account) for c in batch.changes])
            accepted+=1
        except Rejected as exc:
            rejected+=1
            reason=str(exc)
            rejection_reasons[reason]=rejection_reasons.get(reason,0)+1
            assert l.snapshot()==before,(seed,step,"failed operation mutated ledger")
        audited_paths+=l.audit()
        peak=max(peak,sum(max(0,l.net_deposits[u]) for u in users))
    # Choose a real full path without pricing assumptions, then finalize in order.
    possible=list(oracle.paths(market,l.support))
    actual=r.choice(possible)
    for t,state in enumerate(actual[1:],1):
        prior={u:l.bounds(u).minimum for u in l.accounts}
        if l.support[t]!=frozenset({state}):
            l.confirm({t:{state}},"resolver")
        assert all(l.bounds(u).minimum>=prior[u] for u in l.accounts)
        audited_paths+=l.audit()
        # Exercise withdrawal against still-lazy resolved entries.
        for u in users:
            amount=l.bounds(u).minimum
            if amount:execute(l,(change(l,u,external=-amount),),f"final-withdraw-{t}-{u}")
        audited_paths+=l.audit()
    l.settle({},"resolver")
    for u in l.accounts:l.claim(u,u)
    audited_paths+=l.audit()
    assert l.escrow==0
    assert sum(l.wallets.values())==l.endowment
    return {"seed":seed,"accepted":accepted,"rejected":rejected,"skipped_resolved_cover":skipped,
            "rejection_reasons":rejection_reasons,"path_audits":audited_paths,
            "peak_sum_positive_net_deposits":peak,"final_escrow":l.escrow,
            "terminal_path":actual}


def benchmark():
    rows=[]
    # Verifier benchmarks, NOT EVM gas or production latency estimates.
    for kind,n,t in (("free",10,4),("free",40,6),("free",100,8),
                     ("monotone",10,4),("monotone",40,6),("monotone",100,8)):
        setup_start=time.perf_counter()
        m,values=checkpoint_market(f"benchmark-{kind}-{n}-{t}",(tuple(range(n)),)*t,
                                   (lambda a,b:True) if kind=="free" else (lambda a,b:a<=b))
        c=checkpoint_cover(m,values,"terminal ramp",t,lambda x:x*100)
        covers={c.identifier:c}
        account=Account(10_000,((c.identifier,-1),))
        build_ms=(time.perf_counter()-setup_start)*1000
        # Warm the immutable graph's structural classification separately.
        classification_start=time.perf_counter()
        _=m.suffix_starts
        classification_ms=(time.perf_counter()-classification_start)*1000
        times=[]
        for _ in range(7):
            start=time.perf_counter()
            result=extrema(m,account,covers)
            times.append((time.perf_counter()-start)*1000)
        generic_times=[]
        for _ in range(3):
            start=time.perf_counter()
            generic=extrema(m,account,covers,optimized=False)
            generic_times.append((time.perf_counter()-start)*1000)
        assert (result.minimum,result.maximum)==(generic.minimum,generic.maximum)
        rows.append({"kind":kind,"values":n,"checkpoints":t,"states":sum(map(len,m.layers)),
                     "edges":sum(map(len,m.edges)),"normal_path_upper_bound":str(n**t),
                     "graph_build_and_cover_ms":round(build_ms,4),
                     "structural_classification_ms":round(classification_ms,4),
                     "median_ms":round(statistics.median(times),4),"work":result.work,
                     "generic_median_ms":round(statistics.median(generic_times),4),
                     "generic_work":generic.work,
                     "speedup":round(statistics.median(generic_times)/statistics.median(times),2),
                     "minimum":result.minimum})
    return rows


def example_results():
    l,values,h,k=football()
    paths=l.audit()
    football_result={"maker_contribution":l.net_deposits["maker"],"separate_contributions":140,
                     "escrow":l.escrow,"paths_checked":paths}
    l.confirm({2:{1}},"resolver")
    football_result["window_buyer_withdrawable_after_1_1"]=l.bounds("h_buyer").minimum
    l.audit()
    p,values,a,b=price_market()
    p.register("maker",1000)
    return {"rainfall":rainfall_replay(),"football":football_result,
            "free_price":{"two_checkpoint_gross_backing":p.funding("maker",((a,-1),(b,-1)))["deposit"]}}


def run(seeds=100,steps=60):
    start=time.perf_counter()
    replays=[randomized_replay(seed,steps) for seed in range(seeds)]
    return {"schema":"ascemarket-v2-research-results-1",
            "scope":"Synthetic accounting replay; no historical feed, executable market prices or profitability backtest.",
            "environment":{"python":platform.python_version(),"platform":platform.platform()},
            "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted(Path(__file__).parent.glob("*.py"))},
            "examples":example_results(),
            "randomized":{"seeds":seeds,"steps_per_seed":steps,
                          "accepted":sum(x["accepted"] for x in replays),
                          "rejected_without_mutation":sum(x["rejected"] for x in replays),
                          "skipped_resolved_cover":sum(x["skipped_resolved_cover"] for x in replays),
                          "path_audits":sum(x["path_audits"] for x in replays),
                          "all_final_escrows_zero":all(x["final_escrow"]==0 for x in replays),
                          "seed_results":replays},
            "benchmarks":benchmark(),"runtime_seconds":round(time.perf_counter()-start,3)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("model_v2/results.json"))
    parser.add_argument("--seeds",type=int,default=100)
    parser.add_argument("--steps",type=int,default=60)
    args=parser.parse_args()
    if args.seeds<1 or args.steps<1:parser.error("positive seeds and steps required")
    results=run(args.seeds,args.steps)
    args.output.write_text(json.dumps(results,indent=2)+"\n")
    brief={k:v for k,v in results["randomized"].items() if k!="seed_results"}
    print(json.dumps({"output":str(args.output),**brief,"runtime_seconds":results["runtime_seconds"]},indent=2))


if __name__=="__main__":main()
