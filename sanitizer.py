"""Defensive layer. Bright Data's own docs warn: treat scraped web content as
untrusted. Verdict gates real money, so anything pulled from the web is cleaned
and neutralized before it is allowed near the language model."""
import re

# Lines that look like attempts to hijack the model get neutralized.
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all|the|any|previous|prior|above)[\s\S]{0,40}?instructions",
    r"(?i)disregard[\s\S]{0,30}?(above|previous|prior)",
    r"(?i)you\s+are\s+now\s+",
    r"(?i)system\s*prompt",
    r"(?i)new\s+instructions\s*:",
    r"(?i)act\s+as\s+(?:a\s+)?(?:dan|jailbreak)",
]
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize(text: str, max_chars: int) -> str:
    """Strip control chars, neutralize injection-looking spans, trim, truncate."""
    if not text:
        return ""
    text = _CONTROL_CHARS.sub(" ", text)
    for pat in _INJECTION_PATTERNS:
        text = re.sub(pat, "[neutralized-instruction]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()[:max_chars]
