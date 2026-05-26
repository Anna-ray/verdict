"""Run the full pipeline from the terminal in offline mock mode.

    python run_demo.py "Zenith Global Trading FZE" 50000
    python run_demo.py "Northwind Components Ltd" 12000

Forces USE_MOCK + mock LLM so it works before any keys are configured."""
import os
import sys

os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("LLM_PROVIDER", "mock")

import agent  # noqa: E402  (imported after env is set)

_BADGE = {"APPROVE": "[ APPROVE ]", "ESCALATE": "[ ESCALATE ]", "BLOCK": "[ BLOCK ]"}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Zenith Global Trading FZE"
    amount = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"\nVerdict — due diligence on: {name}\n" + "-" * 60)
    result = agent.run(name, amount, on_step=lambda m: print(f"  · {m}"))
    d = result["decision"]

    print("-" * 60)
    print(f"\n{_BADGE.get(d['verdict'], d['verdict'])}  "
          f"risk {d['risk_score']}/100  ({d['confidence']} confidence)")
    print(f"\n{d['summary']}\n")
    print("Risk factors:")
    for f in d["factors"]:
        print(f"  [{f.get('severity', '?')}] {f.get('finding', '')}")
        print(f"        source: {f.get('source', '')}")
    print(f"\nRecommendation: {d['recommendation']}\n")


if __name__ == "__main__":
    main()
