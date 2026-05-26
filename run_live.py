import sys, agent
name = sys.argv[1] if len(sys.argv) > 1 else "Apple Inc"
amount = sys.argv[2] if len(sys.argv) > 2 else ""
result = agent.run(name, amount, on_step=lambda m: print("  .", m))
d = result["decision"]
print("\n[", d["verdict"], "] risk", d["risk_score"], "/100", d["confidence"])
print(d["summary"])
for f in d["factors"]:
    print("  [", f.get("severity"), "]", f.get("finding"))
    print("      source:", f.get("source"))
print("Recommendation:", d["recommendation"])
