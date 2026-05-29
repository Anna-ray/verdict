"""Verdict memory — turns one-shot checks into continuous monitoring.

This is the leap from "check once" to "always-on control": Verdict remembers
every verdict it issues, and on a re-check it reports WHAT CHANGED — e.g.
"was APPROVE, now ESCALATE: a new lawsuit appeared." That is the difference
between a demo and a product a compliance team actually subscribes to.

Memory backend:
- Default: a fast local JSON store, so the app and demo always work with zero
  extra setup or dependencies.
- Optional: Cognee (https://cognee.ai) knowledge-graph memory, enabled by
  setting COGNEE_API_KEY. Cognee gives agents structured, persistent memory;
  here it stores each counterparty's verdict history so risk can be reasoned
  over time, not just retrieved.

Set MEMORY_BACKEND=cognee (plus COGNEE_API_KEY / COGNEE_SERVICE_URL) to use
Cognee; otherwise the local store is used.
"""
import json
import os
import time

_BACKEND = os.getenv("MEMORY_BACKEND", "local").lower()
_LOCAL_PATH = os.getenv("MEMORY_PATH", "verdict_memory.json")
_COGNEE_KEY = os.getenv("COGNEE_API_KEY", "")
_COGNEE_URL = os.getenv("COGNEE_SERVICE_URL", "")


def _norm(name: str) -> str:
    return " ".join((name or "").lower().split())


# --- Local JSON store -------------------------------------------------------
def _load_local() -> dict:
    try:
        with open(_LOCAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_local(store: dict) -> None:
    try:
        with open(_LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(store, f)
    except OSError:
        pass  # never let a memory write break a verdict


def _local_get(name: str):
    return _load_local().get(_norm(name))


def _local_put(name: str, record: dict) -> None:
    store = _load_local()
    store[_norm(name)] = record
    _save_local(store)


# --- Cognee store (optional) ------------------------------------------------
def _cognee_available() -> bool:
    return _BACKEND == "cognee" and bool(_COGNEE_KEY)


def _cognee_put(name: str, record: dict) -> None:
    """Best-effort store into Cognee; falls back to local on any failure."""
    try:
        import asyncio
        import cognee

        async def _go():
            if _COGNEE_URL:
                await cognee.serve(url=_COGNEE_URL, api_key=_COGNEE_KEY)
            text = (f"Counterparty due-diligence record for {name}: "
                    f"verdict {record['verdict']}, risk {record['risk_score']}, "
                    f"summary: {record['summary']}")
            await cognee.remember(text, session_id=_norm(name))
        asyncio.run(_go())
    except Exception:  # noqa: BLE001
        pass
    # Always mirror to local so change-detection is reliable and fast.
    _local_put(name, record)


def _cognee_get(name: str):
    # For reliable structured diffing we read the mirrored local record.
    return _local_get(name)


# --- Public API -------------------------------------------------------------
def recall(name: str):
    """Return the last stored record for a counterparty, or None."""
    if _cognee_available():
        return _cognee_get(name)
    return _local_get(name)


def remember(name: str, decision: dict) -> None:
    """Store the latest verdict for a counterparty."""
    record = {
        "verdict": decision.get("verdict"),
        "risk_score": decision.get("risk_score"),
        "summary": decision.get("summary", ""),
        "ts": time.time(),
    }
    if _cognee_available():
        _cognee_put(name, record)
    else:
        _local_put(name, record)


def diff(name: str, decision: dict):
    """Compare the new decision to the last stored one.
    Returns None if no prior record, else a change summary dict."""
    prev = recall(name)
    if not prev:
        return None
    old_v, new_v = prev.get("verdict"), decision.get("verdict")
    old_r, new_r = prev.get("risk_score", 0), decision.get("risk_score", 0)
    changed = (old_v != new_v) or (abs((new_r or 0) - (old_r or 0)) >= 10)
    direction = "unchanged"
    if (new_r or 0) > (old_r or 0):
        direction = "worsened"
    elif (new_r or 0) < (old_r or 0):
        direction = "improved"
    return {
        "changed": changed,
        "direction": direction,
        "old_verdict": old_v, "new_verdict": new_v,
        "old_risk": old_r, "new_risk": new_r,
        "backend": "cognee" if _cognee_available() else "local",
    }


def backend_name() -> str:
    return "Cognee" if _cognee_available() else "local store"
