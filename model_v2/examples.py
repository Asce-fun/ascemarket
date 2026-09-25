"""Generic market builders and reproducible, synthetic lifecycle fixtures.

Predicates run only when constructing immutable payout tables, never as ledger hooks.
"""
from dataclasses import replace
from .schema import Market, Cover, Limits, Rejected, integer
from .ledger import Ledger, Change, approve


def checkpoint_market(label, values, allows, *, finality="progressive", limits=Limits()):
    """Each normal checkpoint is contractually finalized when constrained.

    X is an absorbing exceptional branch: cancellation, overflow or missing data.
    It pays unresolved exception amounts while preserving previous checkpoint payouts.
    Observations are finite exact values: this builder NEVER silently caps them.
    """
    values=tuple(tuple(layer) for layer in values)
    if finality=="end" and len(values)>1:
        raise Rejected("multi-checkpoint end-finality needs retained history; use deferred_history_market")
    layers=(("START",),)+tuple(tuple(repr(v) for v in layer)+("EXCEPTION",) for layer in values)
    edges=[tuple((0,w) for w in range(len(layers[1])))]
    for t in range(len(values)-1):
        before,after=values[t],values[t+1]
        entries=[(v,w) for v,x in enumerate(before) for w,y in enumerate(after) if allows(x,y)]
        entries += [(v,len(after)) for v in range(len(before))]
        entries += [(len(before),len(after))]
        edges.append(tuple(entries))
    market=Market(label,layers,tuple(edges),finality=finality,limits=limits,
                  source_rule="Finite harness observations; X is terminal cancellation/overflow/missing data; prior finalized payouts survive")
    return market,values


def checkpoint_cover(market,values,label,checkpoint,payout,*,exception=0):
    integer(checkpoint,"checkpoint",minimum=1,maximum=len(values))
    integer(exception)
    nodes=[]
    for v,x in enumerate(values[checkpoint-1]):
        amount=payout(x)
        integer(amount,"payout")
        nodes.append((checkpoint,v,amount))
    # Cancellation before this cover's checkpoint. Add once on entry into X.
    edges=[]
    if exception:
        edges.append((0,0,len(values[0]),exception))
        for t in range(1,checkpoint):
            for v in range(len(values[t-1])):
                edges.append((t,v,len(values[t]),exception))
    return Cover(market.identifier,label,tuple(nodes),tuple(edges))


def change_cover(market,values,label,start,payout,*,exception=0):
    integer(start,"start checkpoint",minimum=1,maximum=len(values)-1)
    integer(exception)
    edges=[]
    for v,w in market.edges[start]:
        if v<len(values[start-1]) and w<len(values[start]):
            amount=payout(values[start-1][v],values[start][w])
            integer(amount,"change payout")
            edges.append((start,v,w,amount))
    if exception:
        edges.append((0,0,len(values[0]),exception))
        for t in range(1,start+1):
            for v in range(len(values[t-1])):
                edges.append((t,v,len(values[t]),exception))
    return Cover(market.identifier,label,edges=tuple(edges))


def exact_ramp(x,lo,hi,amount):
    """Reject non-integral executable payouts rather than hide rounding."""
    for v in (x,lo,hi,amount): integer(v)
    if hi<=lo or amount<0:
        raise Rejected("invalid ramp")
    if x<=lo: return 0
    if x>=hi: return amount
    numerator=amount*(x-lo)
    if numerator%(hi-lo):
        raise Rejected("ramp not integral at observation tick")
    return numerator//(hi-lo)


def execute(ledger,changes,nonce,fees=()):
    batch=ledger.make_batch(changes,nonce=nonce,fees=fees)
    ledger.execute(batch,[approve(batch,c.account) for c in batch.changes])
    return batch


def change(ledger,who,holdings=(),cash=0,external=0):
    return Change(who,ledger.accounts[who].revision,holdings,cash,external)


def rainfall():
    market,values=checkpoint_market("rainfall",((0,4,12),(0,8,15)),lambda a,b:a<=b)
    ledger=Ledger(market)
    a=ledger.admit(checkpoint_cover(market,values,"rain at noon >= 10",1,lambda x:100 if x>=10 else 0))
    b=ledger.admit(checkpoint_cover(market,values,"evening rain < 10",2,lambda x:100 if x<10 else 0))
    for who in ("maker","buyer_a","buyer_b","treasury"):
        ledger.register(who,1000)
    execute(ledger,(change(ledger,"maker",((a,-1),(b,-1)),80,20),
                    change(ledger,"buyer_a",((a,1),),-30,30),
                    change(ledger,"buyer_b",((b,1),),-50,50)),"rain-open")
    return ledger,values,a,b


def rainfall_replay():
    ledger,values,a,b=rainfall()
    stages=[]
    def record(stage):
        count=ledger.audit()
        stages.append({"stage":stage,"epoch":ledger.epoch,"paths":count,"escrow":ledger.escrow,
                       "withdrawable":{who:ledger.bounds(who).minimum for who in ledger.accounts}})
    record("opened")
    ledger.post_report(1,{2},"resolver")
    record("noon_12_reported_not_final")
    ledger.confirm({1:{2}},"resolver")
    record("noon_12_contractually_final")
    execute(ledger,(change(ledger,"buyer_a",external=-100),),"early-payment")
    record("buyer_withdrew_100")
    ledger.settle({2:{len(values[1])}},"resolver")
    record("later_cancellation_preserves_payment")
    for who in ledger.accounts:
        ledger.claim(who,who)
    record("all_claimed")
    return {"scenario":"synthetic rainfall lifecycle","stages":stages,
            "maker_deposit":20,"separate_obligation_deposits":120,
            "buyer_a_profit":ledger.wallets["buyer_a"]-1000,
            "maker_profit":ledger.wallets["maker"]-1000,
            "note":"Early winning-claim payment, not extra maker collateral release; prices are fixtures."}


def football():
    vals=((1,0),(1,1),(2,0),(2,1),(2,2))
    market,values=checkpoint_market("football",(((1,0),),vals,vals),
                                    lambda a,b:a[0]<=b[0] and a[1]<=b[1])
    ledger=Ledger(market)
    h=ledger.admit(change_cover(market,values,"away goal in window",1,lambda a,b:100 if b[1]>a[1] else 0))
    k=ledger.admit(checkpoint_cover(market,values,"final score exactly 1-0",3,lambda x:100 if x==(1,0) else 0))
    for who in ("maker","h_buyer","k_buyer"):
        ledger.register(who,1000)
    ledger.confirm({1:{0}},"resolver")
    execute(ledger,(change(ledger,"maker",((h,-1),(k,-1)),60,40),
                    change(ledger,"h_buyer",((h,1),),-35,35),
                    change(ledger,"k_buyer",((k,1),),-25,25)),"football-open")
    return ledger,values,h,k


def price_market():
    market,values=checkpoint_market("free-price",((2900,3000,3200),)*2,lambda a,b:True)
    ledger=Ledger(market)
    a=ledger.admit(checkpoint_cover(market,values,"range at first checkpoint",1,lambda x:100 if x==3000 else 0))
    b=ledger.admit(checkpoint_cover(market,values,"range at second checkpoint",2,lambda x:100 if x==3000 else 0))
    return ledger,values,a,b


def deferred_history_market(label, observations, allows, *, limits=Limits()):
    """Exact small-market compiler for end-finality with terminal cancellation.

    It augments states with observation history, so prior unfinalized payouts can
    disappear on cancellation. This deliberately exposes exponential state cost;
    large requests are rejected, not silently given progressive finality.
    """
    observations=tuple(tuple(v) for v in observations)
    if not observations or len(observations)+1>limits.max_layers:
        raise Rejected("layer limit")
    histories=[]
    previous=[()]
    total_states=1
    total_edges=0
    edges=[]
    for t,values in enumerate(observations):
        current=[]
        transitions=[]
        for v,prefix in enumerate(previous):
            for value in values:
                if not prefix or allows(prefix[-1],value):
                    if total_states+len(current)+2>limits.max_states:
                        raise Rejected("augmented history state limit")
                    transitions.append((v,len(current)))
                    current.append(prefix+(value,))
        cancel=len(current)
        transitions.extend((v,cancel) for v in range(len(previous)))
        if t:transitions.append((len(previous),cancel))
        total_states+=len(current)+1
        total_edges+=len(transitions)
        if total_edges>limits.max_edges:
            raise Rejected("augmented history edge limit")
        histories.append(tuple(current))
        edges.append(tuple(transitions))
        previous=current
    layers=(("START",),)+tuple(tuple(repr(h) for h in hs)+("EXCEPTION",) for hs in histories)
    market=Market(label,layers,tuple(edges),finality="end",limits=limits,
                  source_rule="Full retained observation history; no intermediate final payouts; cancellation pays declared unresolved amount")
    return market,tuple(histories)


def deferred_cover(market,histories,label,payout,*,exception=0):
    """Terminal table for bounded path functions on a predeclared history graph."""
    if market.finality!="end":
        raise Rejected("deferred cover requires end-finality graph")
    t=len(histories)
    nodes=[(t,v,payout(history)) for v,history in enumerate(histories[-1])]
    nodes.append((t,len(histories[-1]),exception))
    return Cover(market.identifier,label,tuple(nodes),
                 terms="End-finality path table; no checkpoint payout survives pre-final cancellation")
