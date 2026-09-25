"""Exact bounded node/edge dynamic program, including a worst-case witness."""
from dataclasses import dataclass
from .schema import Rejected, integer


@dataclass(frozen=True)
class Extremes:
    minimum: int
    maximum: int
    witness: tuple[int, ...]
    work: int


def validate_support(market, support):
    if len(support) != len(market.layers):
        raise Rejected("support layer mismatch")
    out=[]
    for t, layer in enumerate(support):
        for v in layer:
            integer(v, "support state", minimum=0, maximum=len(market.layers[t])-1)
        out.append(frozenset(layer))
    return tuple(out)


def compile_factors(market, account, covers):
    lim = market.limits
    lim.checked(account.cash)
    if len(account.holdings) > lim.max_holdings:
        raise Rejected("holding limit")
    nodes = [[0]*len(layer) for layer in market.layers]
    edges = [{} for _ in market.edges]
    terms = 0
    # A conservative representation bound ensures later lazy resolution cannot
    # overflow solely because offsetting factors were materialized separately.
    arithmetic_budget = abs(account.cash)
    for cid, q in account.holdings:
        if cid not in covers:
            raise Rejected("unknown cover")
        lim.checked(q)
        cover = covers[cid]
        arithmetic_budget = lim.checked(arithmetic_budget + abs(q) *
            (sum(abs(row[-1]) for row in cover.nodes) + sum(abs(row[-1]) for row in cover.edges)))
        terms += len(cover.nodes)+len(cover.edges)
        if terms > lim.max_terms:
            raise Rejected("combined factor limit")
        for t,v,amount in cover.nodes:
            nodes[t][v] = lim.checked(nodes[t][v]+lim.checked(q*amount))
        for t,v,w,amount in cover.edges:
            key=(v,w)
            edges[t][key] = lim.checked(edges[t].get(key,0)+lim.checked(q*amount))
    edges = [{key:value for key,value in layer.items() if value} for layer in edges]
    return nodes, edges, terms


def extrema(market, account, covers, support=None, *, optimized=True):
    support = validate_support(market, market.full_support if support is None else support)
    nodes, costs, terms = compile_factors(market, account, covers)
    checked = market.limits.checked
    last = len(market.layers)-1
    low = {v:nodes[last][v] for v in support[last]}
    high = dict(low)
    choices = [{} for _ in market.edges]
    work = len(low)+terms
    for t in reversed(range(last)):
        next_low, next_high = {}, {}
        # Do not replace a sparse edge scan with a more expensive full suffix scan.
        # This also keeps actual work within the admission V+E budget.
        use_suffix=(optimized and not costs[t]
                    and len(market.edges[t])>=len(market.layers[t+1]))
        starts=market.suffix_starts[t] if use_suffix else None
        if starts is not None:
            # Exact suffix min/max, including holes from final facts and dead states.
            width=len(market.layers[t+1])
            suffix=[None]*width
            best_low=best_high=arg=None
            for w in reversed(range(width)):
                work+=1
                if w in low:
                    if best_low is None or low[w]<=best_low:
                        best_low,arg=low[w],w
                    best_high=high[w] if best_high is None else max(best_high,high[w])
                if arg is not None:
                    suffix[w]=(best_low,best_high,arg)
            for v in sorted(support[t]):
                start=starts[v]
                if start is None or suffix[start] is None:
                    continue
                a,b,w=suffix[start]
                next_low[v]=checked(nodes[t][v]+a)
                next_high[v]=checked(nodes[t][v]+b)
                choices[t][v]=w
            low,high=next_low,next_high
            work+=len(low)
            continue
        for v,w in market.edges[t]:
            work += 1
            if v not in support[t] or w not in low:
                continue
            a = checked(nodes[t][v]+checked(costs[t].get((v,w),0)+low[w]))
            b = checked(nodes[t][v]+checked(costs[t].get((v,w),0)+high[w]))
            if v not in next_low or a < next_low[v]:
                next_low[v]=a
                choices[t][v]=w
            next_high[v]=max(next_high.get(v,b),b)
        low, high = next_low, next_high
        work += len(low)
    if not low:
        raise Rejected("empty support")
    start = min(low, key=lambda v:(low[v],v))
    witness=[start]
    for t in range(last):
        witness.append(choices[t][witness[-1]])
    return Extremes(checked(account.cash+low[start]),
                    checked(account.cash+max(high.values())), tuple(witness), work)
