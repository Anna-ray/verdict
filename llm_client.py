"""Model layer. One generate(system, user) -> str entrypoint, three providers.
The SDKs are imported lazily so 'mock' mode runs on the standard library alone."""
import json
import re

import brightdata_client  # only used by the mock provider, for citation URLs
import config


def generate(system: str, user: str) -> str:
    provider = config.LLM_PROVIDER
    if provider == "gemini":
        return _gen_gemini(system, user)
    if provider == "groq":
        return _gen_groq(system, user)
    if provider == "aimlapi":
        return _gen_aimlapi(system, user)
    return _gen_mock(system, user)


def _gen_aimlapi(system: str, user: str) -> str:
    """AI/ML API — one OpenAI-compatible endpoint, hundreds of models."""
    from openai import OpenAI
    client = OpenAI(api_key=config.AIMLAPI_KEY,
                    base_url="https://api.aimlapi.com/v1")
    resp = client.chat.completions.create(
        model=config.AIMLAPI_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


def _gen_gemini(system: str, user: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL, system_instruction=system)
    resp = model.generate_content(user)
    return resp.text


def _gen_groq(system: str, user: str) -> str:
    from groq import Groq
    client = Groq(api_key=config.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


def _gen_mock(system: str, user: str) -> str:
    """Heuristic stand-in so the offline demo produces a realistic verdict."""
    sources = brightdata_client.extract_urls(user, limit=3) or ["(no source)"]
    low = user.lower()
    risk_terms = ["fine", "fined", "fraud", "sanction", "lawsuit", "scam",
                  "non-payment", "undisclosed", "not disclosed", "no audited",
                  "opaque", "high-risk", "complaint", "unpaid", "investigation"]
    hits = [t for t in risk_terms if t in low]

    if len(hits) >= 2:
        payload = {
            "verdict": "BLOCK",
            "risk_score": 86,
            "confidence": "HIGH",
            "summary": "Multiple high-severity red flags: opaque ownership, a "
                       "regulatory penalty, and supplier non-payment reports.",
            "factors": [
                {"finding": "Beneficial ownership undisclosed; no audited "
                            "financials on file.",
                 "severity": "CRITICAL", "source": sources[0]},
                {"finding": "Regulator penalty cited for undisclosed ownership "
                            "structure (layering risk).",
                 "severity": "HIGH",
                 "source": sources[1] if len(sources) > 1 else sources[0]},
                {"finding": "Several suppliers report unpaid invoices and "
                            "unreachable contacts.",
                 "severity": "HIGH",
                 "source": sources[2] if len(sources) > 2 else sources[0]},
            ],
            "recommendation": "Do not release payment. Escalate to compliance "
                              "for enhanced due diligence and ownership "
                              "verification before any engagement.",
        }
    else:
        payload = {
            "verdict": "APPROVE",
            "risk_score": 12,
            "confidence": "HIGH",
            "summary": "Long operating history, audited financials, and a clean "
                       "reputation with no adverse findings.",
            "factors": [
                {"finding": "Established multi-decade entity with audited "
                            "accounts filed.",
                 "severity": "LOW", "source": sources[0]},
                {"finding": "Positive industry recognition; no litigation on "
                            "record.",
                 "severity": "LOW",
                 "source": sources[1] if len(sources) > 1 else sources[0]},
            ],
            "recommendation": "Proceed with payment under standard monitoring.",
        }
    return json.dumps(payload)


def parse_json(raw: str) -> dict:
    """Robustly pull a JSON object out of a model response."""
    if not raw:
        raise ValueError("empty model response")
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(),
                     flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model response")
    return json.loads(cleaned[start:end + 1])
