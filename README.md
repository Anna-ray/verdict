# Verdict

**Autonomous counterparty due diligence — reads the live web before you wire a dollar.**

Verdict is an AI agent that vets a business counterparty in real time. Given a
vendor or invoice, it searches and reads the live web (company sites, registries,
news, adverse-media), then returns a grounded verdict — **APPROVE / ESCALATE /
BLOCK** — with a cited source behind every claim.

Built for the Bright Data *Web Data UNLOCKED* hackathon. The live web is hostile
to automation (rate limits, bot detection, CAPTCHAs, geo-blocks); Verdict uses
the **Bright Data MCP server** to see the real, current web instead of stale data.

---

## Quickstart (offline, zero keys)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # already set to offline mock mode

# CLI demo (no UI):
python run_demo.py "Zenith Global Trading FZE" 50000
python run_demo.py "Northwind Components Ltd" 12000

# Web UI:
python app.py
```

Mock mode runs the entire pipeline (search → scrape → sanitize → verdict) on
canned data, so you can build and test the agent and UI before any API keys are
ready.

## Go live (when your keys work)

Edit `.env`:

```env
USE_MOCK=false
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
BRIGHTDATA_API_TOKEN=...
```

Nothing else changes — same code path, real data.

## Architecture

```
app.py            Gradio UI (dark navy/teal), streams the investigation
run_demo.py       CLI runner (forces offline mock)
agent.py          Agent loop: discover → access → extract → sanitize
brightdata_client Bright Data MCP wrapper (search_engine, scrape_as_markdown)
sanitizer.py      Treats scraped content as untrusted (prompt-injection guard)
verdict_engine.py Grounded prompt → cited APPROVE/ESCALATE/BLOCK verdict
llm_client.py     Provider abstraction: mock / gemini / groq
mock_data.py      Canned web data for offline development
config.py         All settings, read from .env
```

## Why each scoring axis is covered

- **Bright Data integration (load-bearing):** the agent literally cannot run
  without live web access via the MCP server — search + structured scraping.
- **Business impact:** every B2B payment needs counterparty risk checks; this
  automates a control enterprises pay for today.
- **Trust engineering:** scraped content is sanitized before it reaches the
  model, mitigating prompt injection — non-negotiable when gating money.

## Deploy (Hugging Face Space)

1. Create a Space, SDK = **Gradio**, and push these files (`app.py` at root).
2. In Space **Settings → Secrets**, add: `USE_MOCK=false`, `LLM_PROVIDER=gemini`,
   `GEMINI_API_KEY`, `BRIGHTDATA_API_TOKEN`.
3. The Space URL is your "working prototype others can use online" deliverable.

## Notes

- Stay on Bright Data's **free tier** — base tools (`search_engine`,
  `scrape_as_markdown`) are all Verdict needs. Do **not** enable `PRO_MODE`.
- The demo counterparties are illustrative names, not real companies.
