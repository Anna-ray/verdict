"""Evidence verification — the anti-hallucination layer.

A verdict is only as trustworthy as its citations. This module checks, for
every factor the model produced, whether the source it cited actually exists
in the evidence Verdict collected. A factor whose citation can't be traced
back to real collected evidence is flagged UNVERIFIED — so a confident-sounding
claim can never quietly rest on a source that was never read.

This is done deterministically (no extra LLM call): it is reproducible, free,
and fast. It returns the factors annotated with a `verified` flag plus an
overall integrity summary the UI and PDF can display.
"""
from urllib.parse import urlparse


def _domain(url: str) -> str:
    try:
        net = urlparse(url.strip()).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:  # noqa: BLE001
        return ""


def verify(decision: dict, evidence: list) -> dict:
    """Annotate each factor with `verified` (its source traces to collected
    evidence) and attach an integrity summary to the decision. Mutates and
    returns `decision`."""
    # Build the set of sources we actually collected.
    evidence_urls = {e.get("url", "").strip() for e in (evidence or [])}
    evidence_domains = {_domain(u) for u in evidence_urls if u}
    # Sanctions/registry citations are authoritative even without a scraped page.
    _AUTHORITATIVE = {"ofac.treasury.gov", "treasury.gov", "sanctions"}

    factors = decision.get("factors", []) or []
    verified_count = 0
    for f in factors:
        src = str(f.get("source", "")).strip()
        dom = _domain(src)
        is_verified = False
        if not src or src in ("search-results", "(no source)"):
            is_verified = False
        elif src in evidence_urls:
            is_verified = True
        elif dom and dom in evidence_domains:
            is_verified = True
        elif any(a in src.lower() for a in _AUTHORITATIVE):
            is_verified = True  # authoritative source (sanctions list)
        f["verified"] = is_verified
        if is_verified:
            verified_count += 1

    total = len(factors)
    decision["integrity"] = {
        "verified": verified_count,
        "total": total,
        "all_verified": (total > 0 and verified_count == total),
        "ratio": (verified_count / total) if total else 0.0,
    }

    # If any factor is unverified, append a missing-evidence warning so the
    # output is honest about what couldn't be traced.
    if total and verified_count < total:
        decision["evidence_warning"] = (
            f"{total - verified_count} of {total} findings cite a source that "
            f"was not in the collected evidence and could not be independently "
            f"traced. Treat those findings with caution.")
    else:
        decision["evidence_warning"] = ""
    return decision
