"""Hindsight wrapper: bank setup, retain, recall, reflect, reset."""
from datetime import datetime, timezone
from functools import lru_cache

from hindsight_client import Hindsight

from backend.config import settings
from backend.retry import with_retries
from backend.schemas import MemoryItem

BANK_NAME = "RunbookMind - Acme Payments SRE"
BANK_MISSION = (
    "You are a cautious, evidence-first SRE assistant for Acme Payments. Prefer reversible actions "
    "(roll back before debugging), always cite the incident ID of precedent, treat engineer feedback "
    "(what worked and what failed) as stronger evidence than a single postmortem, and never invent incidents."
)


@lru_cache(maxsize=1)
def client() -> Hindsight:
    return Hindsight(base_url=settings.hindsight_base_url, api_key=settings.hindsight_api_key, timeout=60.0)


@with_retries()
def ensure_bank() -> None:
    """Create the bank with mission and disposition (idempotent: updates if it already exists)."""
    client().create_bank(
        bank_id=settings.bank_id,
        name=BANK_NAME,
        mission=BANK_MISSION,
        disposition_skepticism=4,  # demand evidence before suggesting a cause
        disposition_literalism=4,  # stick to what the records say
        disposition_empathy=2,
    )


@with_retries()
def retain(content: str, context: str, timestamp: datetime | None = None) -> None:
    client().retain(
        bank_id=settings.bank_id,
        content=content,
        context=context,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


@with_retries()
def retain_many(items: list[dict]) -> None:
    """items: [{content, context, timestamp}]"""
    client().retain_batch(bank_id=settings.bank_id, items=items)


def _to_item(r) -> MemoryItem:
    when = getattr(r, "occurred_start", None) or getattr(r, "mentioned_at", None)
    return MemoryItem(
        text=r.text,
        type=getattr(r, "type", None),
        date=str(when)[:10] if when else None,
        context=getattr(r, "context", None),
    )


@with_retries()
def recall(query: str, max_tokens: int = 3000) -> list[MemoryItem]:
    resp = client().recall(bank_id=settings.bank_id, query=query, max_tokens=max_tokens, budget="mid")
    return [_to_item(r) for r in resp.results]


@with_retries(attempts=2)
def reflect(query: str, context: str | None = None) -> str:
    resp = client().reflect(bank_id=settings.bank_id, query=query, context=context, budget="low")
    return resp.text or ""


def reset_bank() -> None:
    """Delete the demo bank and recreate it (demo use only)."""
    try:
        client().delete_bank(settings.bank_id)
    except Exception:  # noqa: BLE001 - bank may not exist yet
        pass
    ensure_bank()
