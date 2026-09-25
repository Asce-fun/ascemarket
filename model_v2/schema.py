"""Immutable finite-graph markets and integer node/edge payout definitions.

Observation adapters build these objects; the ledger has no event-specific logic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from functools import cached_property
import json


class Rejected(ValueError):
    """An invalid request; ledger operations must leave state unchanged."""


def integer(value, label="amount", *, minimum=None, maximum=None):
    if type(value) is not int:
        raise Rejected(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise Rejected(f"{label} below minimum")
    if maximum is not None and value > maximum:
        raise Rejected(f"{label} above maximum")
    return value


def name(value, label="identifier"):
    if not isinstance(value, str) or not value or len(value) > 256:
        raise Rejected(f"invalid {label}")
    return value


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class Limits:
    # Research guardrails, NOT measured contract gas limits.
    max_layers: int = 32
    max_states: int = 20_000
    max_edges: int = 200_000
    max_covers: int = 256
    max_holdings: int = 64
    max_terms: int = 200_000
    max_batch_accounts: int = 64
    max_fees: int = 128
    max_batch_work: int = 4_000_000
    max_fact_work: int = 8_000_000
    max_abs: int = 2**127 - 1

    def __post_init__(self):
        for k, v in asdict(self).items():
            integer(v, k, minimum=1)

    def checked(self, value):
        return integer(value, "arithmetic", minimum=-self.max_abs, maximum=self.max_abs)


@dataclass(frozen=True)
class Market:
    label: str
    layers: tuple[tuple[str, ...], ...]
    edges: tuple[tuple[tuple[int, int], ...], ...]
    finality: str = "progressive"
    source_rule: str = "Harness final observations; every exceptional branch is explicit in graph"
    asset: str = "UNIT"
    domain: str = "ascemarket-v2-research"
    resolver: str = "resolver"
    admin: str = "admin"
    limits: Limits = Limits()
    close_at: int = 1_000_000

    def __post_init__(self):
        for k in ("label", "source_rule", "asset", "domain", "resolver", "admin"):
            name(getattr(self, k), k)
        integer(self.close_at, "close", minimum=1)
        if not isinstance(self.limits, Limits):
            raise Rejected("invalid limits")
        if self.finality not in ("progressive", "end"):
            raise Rejected("unsupported finality")
        layers = tuple(tuple(layer) for layer in self.layers)
        edges = tuple(tuple(sorted(tuple(e) for e in layer)) for layer in self.edges)
        object.__setattr__(self, "layers", layers)
        object.__setattr__(self, "edges", edges)
        if not layers or len(layers) > self.limits.max_layers:
            raise Rejected("layer limit")
        if len(edges) != len(layers)-1:
            raise Rejected("one edge table per adjacent layer required")
        if sum(map(len, layers)) > self.limits.max_states:
            raise Rejected("state limit")
        if sum(map(len, edges)) > self.limits.max_edges:
            raise Rejected("edge limit")
        for layer in layers:
            if not layer or len(set(layer)) != len(layer):
                raise Rejected("empty or duplicate states")
            for state in layer:
                name(state, "state")
        for t, layer in enumerate(edges):
            if len(set(layer)) != len(layer):
                raise Rejected("duplicate transition")
            for edge in layer:
                if len(edge) != 2:
                    raise Rejected("invalid edge")
                v, w = edge
                integer(v, "edge source", minimum=0, maximum=len(layers[t])-1)
                integer(w, "edge target", minimum=0, maximum=len(layers[t+1])-1)
        reachable = set(range(len(layers[0])))
        for layer in edges:
            reachable = {w for v, w in layer if v in reachable}
        if not reachable:
            raise Rejected("market has no terminal path")

    @cached_property
    def identifier(self):
        return digest({"schema": "finite-path-market-v2", **asdict(self)})

    @property
    def full_support(self):
        return tuple(frozenset(range(len(layer))) for layer in self.layers)

    @cached_property
    def suffix_starts(self):
        """Prove each row is a suffix of the next layer, once per immutable graph.

        None means generic adjacency is required. Empty rows have no continuation.
        This is a structural test, not a claim that every monotone market qualifies.
        """
        result=[]
        for t, edges in enumerate(self.edges):
            adjacency=[[] for _ in self.layers[t]]
            for v,w in edges:
                adjacency[v].append(w)
            width=len(self.layers[t+1])
            starts=[]
            for row in adjacency:
                if not row:
                    starts.append(None)
                elif row == list(range(row[0],width)):
                    starts.append(row[0])
                else:
                    starts=None
                    break
            result.append(None if starts is None else tuple(starts))
        return tuple(result)

    @property
    def work(self):
        return sum(map(len, self.layers)) + sum(map(len, self.edges))


@dataclass(frozen=True)
class Cover:
    market: str
    label: str
    # Sparse exact integer payouts; unspecified factors are zero.
    nodes: tuple[tuple[int, int, int], ...] = ()
    edges: tuple[tuple[int, int, int, int], ...] = ()
    terms: str = "Explicit graph payout; exceptional branches included"
    lot: str = "one integral payout lot"
    trade_until: int = 1_000_000

    def __post_init__(self):
        for key in ("market", "label", "terms", "lot"):
            name(getattr(self, key), key)
        integer(self.trade_until, "trade deadline", minimum=0)
        for field, width in (("nodes", 3), ("edges", 4)):
            entries = tuple(tuple(row) for row in getattr(self, field))
            for row in entries:
                if len(row) != width:
                    raise Rejected("invalid factor")
                for x in row:
                    integer(x, "factor")
            if len({row[:-1] for row in entries}) != len(entries):
                raise Rejected("duplicate factor")
            object.__setattr__(self, field, tuple(sorted(row for row in entries if row[-1])))

    def validate(self, market):
        if self.market != market.identifier:
            raise Rejected("cover belongs to another market")
        if len(self.nodes)+len(self.edges) > market.limits.max_terms:
            raise Rejected("cover term limit")
        for t, v, amount in self.nodes:
            integer(t, "layer", minimum=0, maximum=len(market.layers)-1)
            integer(v, "state", minimum=0, maximum=len(market.layers[t])-1)
            market.limits.checked(amount)
        allowed = tuple(set(layer) for layer in market.edges)
        for t, v, w, amount in self.edges:
            integer(t, "edge layer", minimum=0, maximum=len(market.edges)-1)
            if (v, w) not in allowed[t]:
                raise Rejected("payout on nonexistent edge")
            market.limits.checked(amount)

    @cached_property
    def identifier(self):
        return digest({"language": "integer-node-edge-v2", **asdict(self)})


@dataclass(frozen=True)
class Account:
    cash: int = 0
    holdings: tuple[tuple[str, int], ...] = ()
    revision: int = 0

    def __post_init__(self):
        integer(self.cash)
        integer(self.revision, "revision", minimum=0)
        rows = tuple(tuple(row) for row in self.holdings)
        seen = set()
        for cid, qty in rows:
            name(cid, "cover id")
            integer(qty, "lots")
            if cid in seen:
                raise Rejected("duplicate holding")
            seen.add(cid)
        object.__setattr__(self, "holdings", tuple(sorted((c,q) for c,q in rows if q)))
