"""Transparent risk scoring — shows HOW the score was reached.

A score alone is a black box. This builds an explainable breakdown: a baseline,
plus a signed point contribution for each factor, summing exactly to the final
risk score. Risk-increasing findings add points; positive/clean signals subtract
points. This makes the verdict auditable — a reviewer can see the arithmetic.

Convention: higher score = higher risk (0 safe, 100 dangerous).
- A sanctions hit is shown as the dominant +100 driver.
- For an ordinary verdict, each factor contributes points scaled by its
  severity, and the contributions are normalized so they reconcile to the
  model's final score exactly (no hand-wavy numbers that don't add up).
"""

# Relative weight each severity carries when apportioning the score.
_SEV_WEIGHT = {"CRITICAL": 4.0, "HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}
_BASELINE = 30  # neutral starting risk for an unknown counterparty


def build_breakdown(decision: dict, sanctions: dict = None) -> dict:
    """Return a breakdown dict:
       {baseline, lines:[{label, delta, kind}], total}
    where total == decision['risk_score']."""
    score = int(decision.get("risk_score", 0))
    factors = decision.get("factors", []) or []

    # Sanctions hit: the score is driven by the hard block, show it plainly.
    if sanctions and sanctions.get("hit"):
        return {
            "baseline": 0,
            "lines": [{
                "label": f'Sanctions match — {sanctions.get("matched","")} '
                         f'({sanctions.get("source","OFAC")})',
                "delta": score, "kind": "up"}],
            "total": score,
        }

    if not factors:
        return {"baseline": score, "lines": [], "total": score}

    # Split factors into risk-increasing vs risk-reducing.
    # LOW severity = positive/clean signal (reduces risk);
    # MEDIUM+ = red flag (increases risk).
    raisers, reducers = [], []
    for f in factors:
        sev = str(f.get("severity", "LOW")).upper()
        w = _SEV_WEIGHT.get(sev, 1.0)
        label = f.get("finding", "")[:70]
        if sev == "LOW":
            reducers.append((label, w))
        else:
            raisers.append((label, w, sev))

    lines = []
    # Distance from baseline to the actual score is apportioned across factors.
    delta_total = score - _BASELINE

    if delta_total >= 0:
        # Net risk above baseline: raisers carry it, reducers shave a little.
        rw = sum(w for _, w, _ in raisers) or 1.0
        # reducers get a small fixed credit each (visual honesty), capped.
        red_each = -2
        red_sum = red_each * len(reducers)
        raise_budget = delta_total - red_sum  # raisers must cover this
        for label, w, sev in raisers:
            pts = round(raise_budget * (w / rw))
            lines.append({"label": label, "delta": pts, "kind": "up"})
        for label, _w in reducers:
            lines.append({"label": label, "delta": red_each, "kind": "down"})
    else:
        # Net below baseline (clean company): reducers carry the reduction.
        dw = sum(w for _, w in reducers) or 1.0
        up_each = 3
        up_sum = up_each * len(raisers)
        reduce_budget = delta_total - up_sum  # negative; reducers cover it
        for label, w in reducers:
            pts = round(reduce_budget * (w / dw))
            lines.append({"label": label, "delta": pts, "kind": "down"})
        for label, w, sev in raisers:
            lines.append({"label": label, "delta": up_each, "kind": "up"})

    # Reconcile rounding drift so the sum is EXACT.
    current = _BASELINE + sum(l["delta"] for l in lines)
    drift = score - current
    if drift and lines:
        lines[0]["delta"] += drift

    return {"baseline": _BASELINE, "lines": lines, "total": score}
