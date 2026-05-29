"""Central configuration. All knobs live here, read from environment / .env."""
import os

# .env is optional; don't hard-fail if python-dotenv isn't installed yet (mock mode).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Mode -------------------------------------------------------------------
# USE_MOCK=true  -> no network, canned web data. Develop the agent + UI offline.
# USE_MOCK=false -> live Bright Data calls.
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

# --- LLM --------------------------------------------------------------------
# Providers: "mock" (offline), "gemini" (free, AI Studio), "groq" (free fallback).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# AI/ML API (OpenAI-compatible; hundreds of models behind one endpoint)
AIMLAPI_KEY = os.getenv("AIMLAPI_KEY", "")
AIMLAPI_MODEL = os.getenv("AIMLAPI_MODEL", "gpt-4o-mini")

# --- Bright Data ------------------------------------------------------------
BRIGHTDATA_API_TOKEN = os.getenv("BRIGHTDATA_API_TOKEN", "")
# Hosted MCP endpoint (no local Node needed). Free tier base tools are enough.
BRIGHTDATA_MCP_URL = os.getenv("BRIGHTDATA_MCP_URL", "https://mcp.brightdata.com/mcp")

# --- Investigation limits ---------------------------------------------------
MAX_PAGES_TO_SCRAPE = int(os.getenv("MAX_PAGES_TO_SCRAPE", "3"))
MAX_EVIDENCE_CHARS = int(os.getenv("MAX_EVIDENCE_CHARS", "3500"))
MCP_TIMEOUT_SECONDS = int(os.getenv("MCP_TIMEOUT_SECONDS", "180"))
