"""Hindsight wrapper: bank setup, retain, recall, reflect, reset, and entity graph."""
import asyncio
import json
import logging
import warnings

warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", message=".*Unclosed.*")
from datetime import datetime, timezone

from hindsight_client import Hindsight

from backend.config import DATA_DIR, settings
from backend.retry import with_retries
from backend.schemas import MemoryItem

log = logging.getLogger("runbookmind.memory")

BANK_NAME = "RunbookMind - Acme Payments SRE"
BANK_MISSION = (
    "You are a cautious, evidence-first SRE assistant for Acme Payments. Prefer reversible actions "
    "(roll back before debugging), always cite the incident ID of precedent, treat engineer feedback "
    "(what worked and what failed) as stronger evidence than a single postmortem, and never invent incidents."
)


def _ensure_active_loop():
    """Ensure the current thread has an active, open asyncio event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def client() -> Hindsight:
    """Return a Hindsight client ensuring an active event loop for the current execution context."""
    _ensure_active_loop()
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


def _build_fallback_graph() -> dict:
    """Build knowledge graph from data/incidents.json."""
    incidents_path = DATA_DIR / "incidents.json"
    if not incidents_path.exists():
        return {"nodes": [], "edges": []}
    
    incidents = json.loads(incidents_path.read_text(encoding="utf-8"))
    nodes_map = {}
    edges = []
    
    for inc in incidents:
        inc_id = inc["id"]
        nodes_map[inc_id] = {
            "id": inc_id,
            "label": inc_id,
            "type": "incident",
            "group": "incident",
            "color": "#22c55e",
            "info": f"{inc['severity']}: {inc['symptoms'][:80]}...",
            "value": 15,
        }
        for svc in inc.get("services", []):
            if svc not in nodes_map:
                nodes_map[svc] = {
                    "id": svc,
                    "label": svc,
                    "type": "service",
                    "group": "service",
                    "color": "#3b82f6",
                    "info": f"Service: {svc}",
                    "value": 25,
                }
            edges.append({"source": inc_id, "target": svc, "weight": 2, "label": "impacts"})
            
        for resp in inc.get("responders", []):
            if resp not in nodes_map:
                nodes_map[resp] = {
                    "id": resp,
                    "label": resp,
                    "type": "responder",
                    "group": "responder",
                    "color": "#f97316",
                    "info": f"On-call Responder: {resp}",
                    "value": 18,
                }
            edges.append({"source": inc_id, "target": resp, "weight": 1, "label": "resolved_by"})
            
        fam = inc.get("family")
        if fam:
            fam_id = f"family:{fam}"
            if fam_id not in nodes_map:
                nodes_map[fam_id] = {
                    "id": fam_id,
                    "label": fam.replace("_", " ").title(),
                    "type": "family",
                    "group": "family",
                    "color": "#a855f7",
                    "info": f"Incident Pattern: {fam}",
                    "value": 20,
                }
            edges.append({"source": inc_id, "target": fam_id, "weight": 1, "label": "pattern"})

    return {"nodes": list(nodes_map.values()), "edges": edges}


def get_graph() -> dict:
    """Fetch knowledge graph from Hindsight Cloud entities API, with enriched metadata and fallback."""
    try:
        loop = _ensure_active_loop()
        g = loop.run_until_complete(client().entities.get_entity_graph(settings.bank_id, limit=60, min_count=1))
        if g and hasattr(g, "nodes") and g.nodes:
            nodes = []
            for n in g.nodes:
                d = n.data
                lbl = d.label
                # Classify node type
                if lbl.startswith("INC-"):
                    grp, col = "incident", "#22c55e"
                elif any(svc in lbl for svc in ["api", "service", "gateway", "cache", "primary", "node"]):
                    grp, col = "service", "#3b82f6"
                elif any(name in lbl for name in ["Rao", "Patel", "Wei", "Desai", "Rivera", "Mehta"]):
                    grp, col = "responder", "#f97316"
                else:
                    grp, col = "concept", "#a855f7"
                
                nodes.append({
                    "id": d.id,
                    "label": d.label,
                    "mention_count": getattr(d, "mention_count", 1),
                    "color": col,
                    "group": grp,
                    "value": min(35, max(12, int(getattr(d, "mention_count", 1) / 3))),
                })
            edges = []
            for e in g.edges:
                d = e.data
                edges.append({
                    "source": d.source,
                    "target": d.target,
                    "weight": getattr(d, "weight", 1),
                })
            return {"nodes": nodes, "edges": edges, "source": "hindsight_cloud"}
    except Exception as exc:
        log.warning(f"Live Hindsight graph fetch note: {exc}; using dataset graph")
        
    fallback = _build_fallback_graph()
    fallback["source"] = "dataset_graph"
    return fallback
