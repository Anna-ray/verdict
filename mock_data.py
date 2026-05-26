"""Canned web data so the whole pipeline runs offline (USE_MOCK=true).
The demo counterparty 'Zenith Global Trading FZE' is intentionally risky so the
agent has something to flag. A clean counterparty path is included too."""

_RISKY_SERP = """Search results:

1. Zenith Global Trading FZE - Company Profile
   https://example-registry.org/zenith-global-trading-fze
   Free-zone entity registered 3 months ago. No audited financials on file.

2. Regulator fines Zenith Global Trading over undisclosed beneficial ownership
   https://example-news.org/zenith-global-fine
   A regional authority issued a penalty citing opaque ownership structure.

3. Multiple suppliers report non-payment by Zenith Global Trading
   https://example-reviews.org/zenith-complaints
   Several vendors describe unpaid invoices and unreachable contacts.
"""

_RISKY_PAGES = {
    "https://example-registry.org/zenith-global-trading-fze":
        "Entity: Zenith Global Trading FZE. Status: Active. Incorporated 3 months "
        "ago in a free zone. Beneficial owners: not disclosed. Audited accounts: "
        "none filed. Registered capital: minimal.",
    "https://example-news.org/zenith-global-fine":
        "A regional regulator fined Zenith Global Trading FZE for failing to "
        "disclose its beneficial ownership during onboarding checks. The notice "
        "flagged the structure as high-risk for layering.",
    "https://example-reviews.org/zenith-complaints":
        "Forum threads from at least four suppliers allege non-payment of "
        "invoices over the last quarter and report that company contacts stopped "
        "responding after delivery.",
}

_CLEAN_SERP = """Search results:

1. Northwind Components Ltd - Official Site
   https://example-corp.org/northwind
   Established 1998. Audited financials published annually. UK registered.

2. Northwind Components named regional supplier of the year
   https://example-news.org/northwind-award
   Trade body recognized the firm for reliability and on-time delivery.
"""

_CLEAN_PAGES = {
    "https://example-corp.org/northwind":
        "Northwind Components Ltd. Incorporated 1998. Audited accounts filed for "
        "the last 15 years. Long-standing supplier relationships, no litigation "
        "on record.",
    "https://example-news.org/northwind-award":
        "Industry association awarded Northwind Components its supplier-of-the-year "
        "recognition, citing a strong delivery and payment track record.",
}


def _is_clean(query: str) -> bool:
    return "northwind" in query.lower()


def mock_search(query: str) -> str:
    return _CLEAN_SERP if _is_clean(query) else _RISKY_SERP


def mock_scrape(url: str) -> str:
    return _CLEAN_PAGES.get(url) or _RISKY_PAGES.get(url) or "No content retrieved."
