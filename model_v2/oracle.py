"""Slow independent reference: enumerate paths and evaluate raw covers directly.

Does NOT call the optimized factor compiler, recurrence, or resolution materializer.
Resource limits make this suitable only for small-market correctness checks.
"""
from .schema import Rejected


def paths(market, support=None, max_paths=100_000):
    support = market.full_support if support is None else support
    found = 0

    def walk(prefix):
        nonlocal found
        t = len(prefix)-1
        if t == len(market.layers)-1:
            found += 1
            if found > max_paths:
                raise Rejected("exhaustive reference path limit")
            yield tuple(prefix)
            return
        # Deliberately direct edge traversal, independent of DP reachability.
        for v, w in market.edges[t]:
            if v == prefix[-1] and w in support[t+1]:
                yield from walk(prefix+[w])

    for v in sorted(support[0]):
        yield from walk([v])


def cover_value(cover, path):
    return (sum(amount for t,v,amount in cover.nodes if path[t] == v)
            + sum(amount for t,v,w,amount in cover.edges
                  if path[t] == v and path[t+1] == w))


def account_value(account, covers, path):
    return account.cash + sum(q*cover_value(covers[c],path) for c,q in account.holdings)


def extrema(market, account, covers, support=None, max_paths=100_000):
    low = high = None
    witness = None
    count = 0
    for path in paths(market, support, max_paths):
        value = account_value(account, covers, path)
        count += 1
        if low is None or value < low:
            low, witness = value, path
        high = value if high is None else max(high, value)
    if low is None:
        raise Rejected("empty support")
    return low, high, witness, count
