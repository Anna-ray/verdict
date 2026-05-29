"""Run the full Verdict pipeline live from the terminal.

    python run_live.py "Wirecard AG" 50000
    python run_live.py "Apple Inc"

Uses your .env settings (USE_MOCK, LLM_PROVIDER, keys). Prints the verdict,
sanctions status, evidence integrity, and the transparent risk calculation.
"""
import sys

import agent

_BADGE = {"APPROVE": "[ APPROVE ]", "ESCALATE": "[ ESCALATE ]", "BLOCK": "[ BLOCK ]"}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Apple Inc"
    amount = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"\nVerdict — due diligence on: {name}\n" + "-" * 60)
    result = agent.run(name, amount, on_step=lambda m: print(f"  . {m}"))
    d = result["decision"]
    sanc = result.get("sanctions") or {}

    print("-" * 60)
    print(f"\n{_BADGE.get(d['verdict'], d['verdict'])}  "
          f"risk {d['risk_score']}/100  ({d.get('confidence','')} confidence)")
    print("Sanctions:", "HIT - " + sanc.get("matched", "")
          if sanc.get("hit") else "clear")
    integ = d.get("integrity") or {}
    if integ.get("total"):
        print(f"Evidence integrity: {integ['verified']}/{integ['total']} traced")
    print(f"\n{d.get('summary','')}\n")

    print("Risk factors:")
    for f in d.get("factors", []):
        vflag = "verified" if f.get("verified") else "UNVERIFIED"
        print(f"  [{f.get('severity', '?')}] {f.get('finding', '')}  ({vflag})")
        print(f"        source: {f.get('source', '')}")

    bd = d.get("breakdown") or {}
    if bd.get("lines"):
        print(f"\nRisk calculation (base {bd['baseline']}):")
        for l in bd["lines"]:
            sign = "+" if l["delta"] >= 0 else "-"
            print(f"  {sign}{abs(l['delta']):>3}  {l['label']}")
        print(f"  = {bd['total']}/100")

    print(f"\nRecommendation: {d.get('recommendation','')}\n")


if __name__ == "__main__":
    main()
