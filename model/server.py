"""Local HTTP wrapper around the research model, for the payout editor.

Run: python3 -B -m model.server        then open http://127.0.0.1:8111

Standard library only. No wallets, no signatures, no persistence, no money.
Every number it returns comes from the same exact-rational code the tests cover.
"""
from fractions import Fraction as F
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json

from .payoffs import Payoff

HERE = Path(__file__).resolve().parent
PORT = 8111


def build(spec):
    """One traded claim -> a Payoff. Sign convention: what the ACCOUNT receives."""
    kind = spec["kind"]
    amount = F(str(spec.get("amount", 0)))
    lo = spec.get("lower")
    hi = spec.get("upper")
    if kind == "constant":
        claim = Payoff.constant(amount)
    elif kind == "above":
        claim = Payoff.step(F(str(lo)), amount, void=0)
    elif kind == "below":
        claim = Payoff.below(F(str(lo)), amount, void=0)
    elif kind == "between":
        claim = Payoff.interval(F(str(lo)), F(str(hi)), amount, void=0)
    elif kind == "ramp":
        claim = Payoff.ramp(F(str(lo)), F(str(hi)), amount, void=0)
    else:
        raise ValueError(f"unknown kind: {kind}")
    return claim if spec.get("side", "buy") == "buy" else -claim


def combined(positions):
    """The account's whole payoff: every claim, plus the cash each trade moved."""
    total = Payoff.constant(0)
    for spec in positions:
        total = total + build(spec)
        premium = F(str(spec.get("premium", 0)))
        # a buyer pays the premium away; a seller receives it
        total = total + Payoff.constant(-premium if spec.get("side", "buy") == "buy" else premium)
    return total


def segments(profile, lo, hi):
    """Exact affine pieces plus the jumps between them, ready to draw."""
    xs = [F(str(lo))] + [k.x for k in profile.knots if lo < k.x < hi] + [F(str(hi))]
    segs, jumps = [], []
    for a, b in zip(xs, xs[1:]):
        ya = profile.value(a)
        yb = profile.value(b, left_limit=True)
        segs.append([[float(a), float(ya)], [float(b), float(yb)]])
        after = profile.value(b)
        if b != xs[-1] and after != yb:
            jumps.append({"x": float(b), "from": float(yb), "to": float(after)})
    return segs, jumps


def outcome_rows(profile, lo, hi):
    """What the account receives on each side of every boundary it actually has."""
    rows = []
    marks = [k.x for k in profile.knots if lo <= k.x <= hi]
    seen = set()
    for x in [F(str(lo))] + marks + [F(str(hi))]:
        if x in seen:
            continue
        seen.add(x)
        rows.append({
            "x": float(x),
            "left": float(profile.value(x, left_limit=True)),
            "value": float(profile.value(x)),
        })
    return rows


MARKET = {
    "underlying": "ETH / USDC",
    "observation": "settlement price, 25 Sep 2026, 08:00 UTC",
    "reference": 2980,
    "asset": "USDC",
    "domain": [2200, 3800],
}

# Offers a provider is standing behind. In a live venue these arrive from makers;
# here they are fixed so the interface can be exercised without a quote service.
QUOTES = [
    {"id": "q1", "label": "Pays below 2,800",   "kind": "below",   "lower": 2800, "amount": 100, "ask": 22},
    {"id": "q2", "label": "Pays above 3,200",   "kind": "above",   "lower": 3200, "amount": 100, "ask": 32},
    {"id": "q3", "label": "Pays above 3,000",   "kind": "above",   "lower": 3000, "amount": 100, "ask": 48},
    {"id": "q4", "label": "Pays 2,900 – 3,100", "kind": "between", "lower": 2900, "upper": 3100, "amount": 100, "ask": 41},
    {"id": "q5", "label": "Protection below 3,000", "kind": "ramp", "lower": 2800, "upper": 3000, "amount": 200, "ask": 64},
    {"id": "q6", "label": "Ramps 3,000 – 3,400", "kind": "ramp",   "lower": 3000, "upper": 3400, "amount": 200, "ask": 71},
]


def spark(spec, points=26):
    """Tiny normalised outline of a claim, for the glyph on a quote row."""
    claim = build({**spec, "side": "buy"})
    lo, hi = MARKET["domain"]
    step = (hi - lo) / (points - 1)
    ys = [float(claim.value(F(str(lo)) + F(str(step)) * i)) for i in range(points)]
    top = max(ys) or 1
    return [round(y / top, 4) for y in ys]


def describe(profile, lo, hi):
    low, high = profile.extrema()
    argmin = None
    for row in outcome_rows(profile, lo, hi):
        if abs(row["left"] - float(low)) < 1e-9 or abs(row["value"] - float(low)) < 1e-9:
            argmin = row["x"]
            break
    segs, jumps = segments(profile, lo, hi)
    return {
        "segments": segs, "jumps": jumps,
        "minimum": float(low), "maximum": float(high), "argmin": argmin,
        "funding": float(max(F(0), -low)), "withdrawable": float(max(F(0), low)),
        "boundaries": [float(k.x) for k in profile.knots],
        "boundary_count": len(profile.knots),
        "exact_minimum": str(low), "exact_funding": str(max(F(0), -low)),
    }


def evaluate(payload):
    lo, hi = payload.get("domain", MARKET["domain"])
    held = payload.get("positions", [])
    add = payload.get("proposed")

    current = combined(held)
    out = {"current": describe(current, lo, hi), "proposed": None, "trade": None}

    if add:
        after = combined(held + [add])
        out["proposed"] = describe(after, lo, hi)
        premium = F(str(add.get("premium", 0)))
        pays = premium if add.get("side", "buy") == "buy" else -premium
        deposit = max(F(0), -after.extrema()[0]) - max(F(0), -current.extrema()[0])
        out["trade"] = {
            "premium": float(pays),
            "deposit_change": float(deposit),
            "cash_now": float(pays + max(F(0), deposit)),
            "release": float(max(F(0), -deposit)),
            "best": float(after.extrema()[1]),
            "worst": float(after.extrema()[0]),
        }
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        raw = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "editor.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/market":
            book = [{**qt, "spark": spark(qt)} for qt in QUOTES]
            self._send(200, json.dumps({"market": MARKET, "quotes": book}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/evaluate":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            self._send(200, json.dumps(evaluate(payload)))
        except Exception as exc:                      # surface the real reason
            self._send(400, json.dumps({"error": str(exc)}))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"payout editor  ->  http://127.0.0.1:{PORT}")
    print("exact rational arithmetic; no money, no signatures, no persistence")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
