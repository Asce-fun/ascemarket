"""Export small language-neutral fixtures with independently stated expected values.

Regenerate deliberately: python3 -B -m model_v2.fixtures
"""
from dataclasses import asdict
import json
from pathlib import Path

from .schema import Account
from .examples import rainfall, price_market


def build():
    rows=[]
    def add(label,market,covers,account,support,minimum,maximum):
        rows.append({"name":label,"market":asdict(market),
                     "covers":[asdict(c) for c in covers.values()],
                     "account":asdict(account),"support":[sorted(s) for s in support],
                     "expected":{"minimum":minimum,"maximum":maximum}})
    l,values,a,b=rainfall()
    add("rainfall combined maker",l.market,l.covers,l.accounts["maker"],l.support,0,100)
    add("winning report is not final",l.market,l.covers,l.accounts["buyer_a"],l.support,0,100)
    l.confirm({1:{2}},"resolver")
    add("noon final and cancellation survives",l.market,l.covers,l.accounts["buyer_a"],l.support,100,100)
    add("maker no extra surplus after noon win",l.market,l.covers,l.accounts["maker"],l.support,0,0)
    add("withdrawal removes entitlement once",l.market,l.covers,Account(-100,((a,1),)),l.support,0,0)
    p,values,a,b=price_market()
    add("free prices can pay twice",p.market,p.covers,Account(0,((a,-1),(b,-1))),p.support,-200,0)
    return {"schema":"ascemarket-v2-exact-fixtures-1","amount_unit":"integer settlement base units",
            "note":"Expected extrema are stated explicitly; not populated from the optimized evaluator.",
            "cases":rows}


def main():
    path=Path(__file__).with_name("fixtures.json")
    path.write_text(json.dumps(build(),indent=2)+"\n")
    print(f"Wrote {path}")


if __name__=="__main__":main()
