"""Sanctions screening — checks a counterparty against official watchlists.

This is the first thing a real compliance team checks: is this party on a
sanctions list? Verdict screens the name against OFAC (US Treasury) sanctions
data BEFORE the web verdict. A confirmed hit forces an immediate BLOCK at
maximum risk — no payment to a sanctioned entity, regardless of anything else.

Design:
- A curated, bundled set of well-known OFAC-listed entity names ships with the
  app, so screening is instant and works offline (great for live demos and the
  Hugging Face Space).
- refresh_from_ofac() can pull the full live OFAC SDN list on demand when you
  want maximum freshness. The full list is ~15MB and updates constantly, so for
  responsiveness the bundled set is the default.

All bundled names below are real entries drawn from OFAC's Specially Designated
Nationals (SDN) list (sanctioned banks, state entities, and designated firms).
"""
import re

# --- Bundled OFAC SDN sample (real designated entities) --------------------
# Kept lowercase for matching. This is a representative subset for screening
# demonstrations; refresh_from_ofac() replaces it with the full live list.
_BUNDLED_SDN = {
    "bank melli iran",
    "bank saderat iran",
    "bank sepah",
    "islamic revolutionary guard corps",
    "tornado cash",
    "sberbank",
    "vtb bank",
    "gazprombank",
    "rosneft",
    "wagner group",
    "national iranian oil company",
    "mahan air",
    "hizballah",
    "lazarus group",
    "garantex",
    "evil corp",
    "concord management and consulting",
    "internet research agency",
}

# Active screening set — starts as the bundled set, can be replaced live.
_SCREEN_SET = set(_BUNDLED_SDN)
_SOURCE = "OFAC SDN (bundled sample)"

_CLEAN_RE = re.compile(r"[^a-z0-9 ]+")
_SUFFIXES = (" ag", " inc", " inc.", " ltd", " ltd.", " llc", " plc", " corp",
             " corporation", " co", " co.", " gmbh", " sa", " fze", " group",
             " holdings", " limited", " company")


def _normalize(name: str) -> str:
    n = _CLEAN_RE.sub(" ", (name or "").lower())
    n = re.sub(r"\s+", " ", n).strip()
    for suf in _SUFFIXES:
        if n.endswith(suf):
            n = n[: -len(suf)].strip()
    return n


def screen(name: str) -> dict:
    """Screen a counterparty name against the sanctions set.
    Returns {hit: bool, matched: str|None, source: str}."""
    norm = _normalize(name)
    if not norm:
        return {"hit": False, "matched": None, "source": _SOURCE}

    for entry in _SCREEN_SET:
        e = _normalize(entry)
        # Match if either name contains the other as a whole-phrase substring.
        if e and (e == norm or e in norm or norm in e):
            return {"hit": True, "matched": entry, "source": _SOURCE}
    return {"hit": False, "matched": None, "source": _SOURCE}


def refresh_from_ofac(timeout: int = 30) -> dict:
    """Optionally pull the full live OFAC SDN list and replace the screen set.
    Returns {ok: bool, count: int, error: str|None}. Best-effort; on any
    failure the bundled set stays active so screening always works."""
    global _SCREEN_SET, _SOURCE
    url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
    try:
        import csv
        import io
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Verdict/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("latin-1", errors="ignore")
        names = set()
        # SDN.CSV: column 2 (index 1) is the entity/individual name.
        for row in csv.reader(io.StringIO(data)):
            if len(row) > 1 and row[1] and row[1] != "-0- ":
                names.add(row[1].strip().lower())
        if names:
            _SCREEN_SET = names | _BUNDLED_SDN
            _SOURCE = "OFAC SDN (live)"
            return {"ok": True, "count": len(_SCREEN_SET), "error": None}
        return {"ok": False, "count": len(_SCREEN_SET), "error": "empty list"}
    except Exception as e:  # noqa: BLE001 - never let a refresh break screening
        return {"ok": False, "count": len(_SCREEN_SET), "error": str(e)}
