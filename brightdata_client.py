"""Bright Data integration. This is the load-bearing dependency: Verdict reads
the LIVE web (sites that block ordinary scrapers) via the Bright Data MCP server.

Free-tier base tools used:
  - search_engine      -> SERP results for a query
  - scrape_as_markdown -> clean markdown of a single page

When USE_MOCK=true everything is served from mock_data (no network)."""
import re
import asyncio
from typing import List

import config

# Don't try to scrape the search engines themselves or Bright Data's own pages.
_SKIP = ("google.", "bing.", "duckduckgo.", "brightdata.", "mcp.brightdata.")
_URL_RE = re.compile(r'https?://[^\s\)\]\>"\'<]+')


# --- Live path (MCP over hosted streamable HTTP) ----------------------------
async def _call_tool_async(tool_name: str, arguments: dict) -> str:
    # Imported lazily so mock mode needs zero extra packages.
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = f"{config.BRIGHTDATA_MCP_URL}?token={config.BRIGHTDATA_API_TOKEN}"
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            parts: List[str] = []
            for block in result.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "\n".join(parts)


def _call_tool(tool_name: str, arguments: dict) -> str:
    return asyncio.run(_call_tool_async(tool_name, arguments))


# --- Public API -------------------------------------------------------------
def search_web(query: str) -> str:
    """Return raw SERP text for a query."""
    if config.USE_MOCK:
        from mock_data import mock_search
        return mock_search(query)
    return _call_tool("search_engine", {"query": query})


def scrape_page(url: str) -> str:
    """Return markdown content of a single page."""
    if config.USE_MOCK:
        from mock_data import mock_scrape
        return mock_scrape(url)
    return _call_tool("scrape_as_markdown", {"url": url})


def extract_urls(serp_text: str, limit: int) -> List[str]:
    """Pull candidate result URLs out of SERP text, deduped and filtered."""
    found: List[str] = []
    for raw in _URL_RE.findall(serp_text or ""):
        u = raw.rstrip('.,);')
        if u in found:
            continue
        if any(s in u for s in _SKIP):
            continue
        found.append(u)
        if len(found) >= limit:
            break
    return found
