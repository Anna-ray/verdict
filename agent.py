"""The agent loop. Given a counterparty, run a live web investigation:
discover -> access -> extract -> sanitize, then hand the evidence to the
verdict engine for the final APPROVE / ESCALATE / BLOCK decision."""
import brightdata_client
import config
import sanitizer
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
    """Full pipeline: investigate -> decide. Returns the complete result."""
    evidence = investigate(name, on_step=on_step)
    if on_step:
        on_step("Synthesizing verdict...")
    decision = verdict_engine.decide(name, amount, evidence)
    return {
        "name": name,
        "amount": amount,
        "evidence": evidence,
        "decision": decision,
    }
