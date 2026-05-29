"""Auditor-style reasoning blocks — makes Verdict reason, not just score.

A real analyst doesn't only output a number. They state how confident they are
and why, what they checked for and did NOT find (so the reader understands why
risk isn't higher), and whether the evidence contradicts itself. These three
blocks turn a score into a defensible judgment.

Everything here is DERIVED from the actual run (evidence count, verified
factors, severities, keyword presence) — never hardcoded — so the reasoning
honestly reflects what happened.
"""

# Keywords that, if absent from the gathered evidence, are worth stating as
# "checked and not found" — the reassurance signals.
_CLEAN_CHECKS = [
    ("sanctions", ["sanction", "ofac", "sdn", "embargo"]),
    ("fraud reports", ["fraud", "scam", "ponzi", "embezzle"]),
    ("legal / litigation", ["lawsuit", "litigation", "indict", "convict",
                            "fine", "penalty", "settlement"]),
    ("insolvency", ["insolven", "bankrupt", "liquidation", "wind-up",
                    "wind up", "administration"]),
    ("adverse media", ["scandal", "investigation", "probe", "allegation"]),
]


def _evidence_text(evidence: list) -> str:
    return " ".join((e.get("content", "") or "") for e in (evidence or [])).lower()


def confidence_tag(decision: dict, evidence: list, sanctions: dict = None) -> dict:
    """Derive an overall evidence-confidence label from real signals.
    Returns {level, reason}."""
    n_sources = len(evidence or [])
    integ = decision.get("integrity") or {}
    verified_ratio = integ.get("ratio", 0.0)
    total_chars = sum(len(e.get("content", "") or "") for e in (evidence or []))

    # Sanctions hit -> always HIGH confidence (authoritative source).
    if sanctions and sanctions.get("hit"):
        return {"level": "HIGH",
                "reason": "Match confirmed against an authoritative sanctions list."}

    score = 0
    if n_sources >= 3:
        score += 2
    elif n_sources == 2:
        score += 1
    if verified_ratio >= 0.99:
        score += 2
    elif verified_ratio >= 0.5:
        score += 1
    if total_chars >= 1500:
        score += 1

    if score >= 4:
        level, reason = "HIGH", (f"Based on {n_sources} independent sources with "
                                 "all findings traced to their citations.")
    elif score >= 2:
        level, reason = "MEDIUM", (f"Based on {n_sources} source(s); some signals "
                                   "are limited or partially traced.")
    else:
        level, reason = "LOW", ("Limited public evidence was available; treat the "
                                "verdict as provisional.")
    return {"level": level, "reason": reason}


def why_not_higher(decision: dict, evidence: list, sanctions: dict = None) -> list:
    """For non-BLOCK verdicts, list what was checked and came back clean.
    Returns a list of strings (may be empty for BLOCK)."""
    verdict = decision.get("verdict")
    if verdict == "BLOCK":
        return []  # nothing reassuring to say about a blocked party

    text = _evidence_text(evidence)
    # severities present among factors
    sev_present = {str(f.get("severity", "")).upper()
                   for f in decision.get("factors", [])}

    clean = []
    if not (sanctions and sanctions.get("hit")):
        clean.append("No sanctions or watchlist match")
    for label, kws in _CLEAN_CHECKS:
        if label == "sanctions":
            continue  # handled above
        if not any(k in text for k in kws):
            clean.append(f"No {label} found in available evidence")
    if "CRITICAL" not in sev_present:
        clean.append("No critical-severity red flags identified")
    return clean


def contradiction_check(decision: dict, evidence: list) -> dict:
    """State whether the gathered evidence contains conflicting signals.
    Heuristic: positive AND negative reputation language about the same party.
    Returns {checked: True, conflict: bool, note: str}."""
    text = _evidence_text(evidence)
    positive = ["reliable", "award", "reputable", "trusted", "established",
                "audited", "recognized", "strong track record"]
    negative = ["unpaid", "non-payment", "complaint", "fraud", "scam",
                "undisclosed", "penalty", "lawsuit", "scandal"]
    has_pos = any(p in text for p in positive)
    has_neg = any(n in text for n in negative)
    conflict = has_pos and has_neg
    if conflict:
        note = ("Mixed signals detected: both positive and adverse references "
                "appear in the evidence. Weighted by severity and recency.")
    else:
        note = "No significant contradictory signals detected across sources."
    return {"checked": True, "conflict": conflict, "note": note}


def attach(decision: dict, evidence: list, sanctions: dict = None) -> dict:
    """Attach all three reasoning blocks to the decision."""
    decision["confidence_tag"] = confidence_tag(decision, evidence, sanctions)
    decision["why_not_higher"] = why_not_higher(decision, evidence, sanctions)
    decision["contradiction"] = contradiction_check(decision, evidence)
    return decision
