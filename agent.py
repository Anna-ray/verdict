"""The agent loop. Given a counterparty, run a live web investigation:
discover -> access -> extract -> sanitize, then hand the evidence to the
verdict engine for the final APPROVE / ESCALATE / BLOCK decision."""
import brightdata_client
import config
import memory
import reasoning
import sanctions
import sanitizer
import scoring
import verdict_engine


def _build_queries(name: str) -> list:
    return [
        f"{name} company official website",
        f"{name} fraud lawsuit sanction scam complaint fine",
        f"{name} reviews reputation supplier",
    ]


def investigate(name: str, on_step=None) -> list:
    """Collect sanitized evidence about a counterparty. Returns a list of
    {url, content} dicts. on_step(msg) is an optional progress callback."""
    def step(msg):
        if on_step:
            on_step(msg)

    evidence = []
    seen_urls = set()
    serp_blob = []

    for q in _build_queries(name):
        step(f"Searching: {q}")
        serp = brightdata_client.search_web(q)
        serp_blob.append(serp)

    combined = "\n".join(serp_blob)
    urls = brightdata_client.extract_urls(combined, limit=config.MAX_PAGES_TO_SCRAPE)

    for url in urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        step(f"Reading: {url}")
        raw = brightdata_client.scrape_page(url)
        clean = sanitizer.sanitize(raw, config.MAX_EVIDENCE_CHARS)
        if clean:
            evidence.append({"url": url, "content": clean})

    # If nothing was scrapeable, still pass the SERP summaries as evidence.
    if not evidence:
        step("No pages scraped; using search summaries as evidence.")
        evidence.append({
            "url": "search-results",
            "content": sanitizer.sanitize(combined, config.MAX_EVIDENCE_CHARS),
        })
    return evidence


def run(name: str, amount: str = "", on_step=None) -> dict:
    """Full pipeline: sanctions screen -> investigate -> decide."""
    def step(msg):
        if on_step:
            on_step(msg)

    # Step 0: sanctions screening. A confirmed hit is an immediate hard BLOCK —
    # no payment to a sanctioned entity, no matter what the web says.
    step("Screening against OFAC sanctions list...")
    sanc = sanctions.screen(name)
    if sanc["hit"]:
        step(f"SANCTIONS HIT: matches '{sanc['matched']}' on {sanc['source']}")
        decision = {
            "verdict": "BLOCK",
            "risk_score": 100,
            "confidence": "HIGH",
            "summary": (f"{name} matches a sanctioned entity on the "
                        f"{sanc['source']} list. Payment is prohibited."),
            "factors": [{
                "finding": (f"Name matches '{sanc['matched']}' on an official "
                            f"sanctions list ({sanc['source']})."),
                "severity": "CRITICAL",
                "source": "https://ofac.treasury.gov/sanctions-list-service",
            }],
            "recommendation": ("Do NOT proceed. Transacting with a sanctioned "
                               "party may be illegal. Escalate to compliance "
                               "immediately."),
        }
        decision["breakdown"] = scoring.build_breakdown(decision, sanc)
        decision = reasoning.attach(decision, [], sanc)
        return {"name": name, "amount": amount,
                "evidence": [], "decision": decision, "sanctions": sanc}

    # No sanctions hit -> proceed with live web due diligence.
    evidence = investigate(name, on_step=on_step)
    step("Synthesizing verdict...")
    decision = verdict_engine.decide(name, amount, evidence)

    # Transparent score breakdown (explainability): how the number was reached.
    decision["breakdown"] = scoring.build_breakdown(decision, sanc)
    # Auditor reasoning: confidence, why-not-higher, contradiction check.
    decision = reasoning.attach(decision, evidence, sanc)

    # Memory: detect change vs the last time we checked this counterparty,
    # then store the new verdict. This is the continuous-monitoring layer.
    change = memory.diff(name, decision)
    if change and change["changed"]:
        step(f"Change since last check ({memory.backend_name()}): "
             f"{change['old_verdict']} -> {change['new_verdict']} "
             f"(risk {change['old_risk']} -> {change['new_risk']})")
    memory.remember(name, decision)

    return {"name": name, "amount": amount, "evidence": evidence,
            "decision": decision, "sanctions": sanc, "change": change}
