"""Bulk loader for synthetic incident dataset into Hindsight memory."""
import argparse
import json
import logging
from datetime import datetime, timezone

from backend import memory
from backend.config import DATA_DIR
from backend.schemas import IngestResponse

log = logging.getLogger("runbookmind.ingest")

def load_incidents() -> list[dict]:
    path = DATA_DIR / "incidents.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing incidents dataset at {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def narrative(inc: dict) -> str:
    """Format incident as a rich natural language postmortem paragraph for Hindsight fact extraction."""
    date_str = str(inc.get("date", ""))[:10]
    sev = inc.get("severity", "Sev2")
    services = ", ".join(inc.get("services", []))
    actions_tried = "; ".join(inc.get("actions_tried", []))
    responders = ", ".join(inc.get("responders", []))
    
    text = (
        f"{inc['id']} ({date_str}, {sev}): {inc['symptoms']}. "
        f"Services involved: {services}. "
        f"Log snippet: \"{inc.get('log_snippet', '')}\". "
        f"Root cause: {inc.get('root_cause', '')}. "
        f"Actions tried: {actions_tried}. "
        f"Resolution: {inc.get('resolution', '')}. "
        f"Permanent fix: {inc.get('permanent_fix', '')}. "
        f"Responders: {responders}."
    )
    return text

def ingest(exclude_family: list[str] | None = None) -> IngestResponse:
    """Ingest incidents from dataset into Hindsight bank, optionally skipping families."""
    incidents = load_incidents()
    excluded = [f.lower() for f in (exclude_family or [])]
    
    retained_count = 0
    for inc in incidents:
        family = inc.get("family", "").lower()
        if family and family in excluded:
            continue
        
        postmortem_text = narrative(inc)
        date_raw = inc.get("date")
        if isinstance(date_raw, str):
            # Parse ISO date with timezone
            try:
                dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.now(timezone.utc)
        elif isinstance(date_raw, datetime):
            dt = date_raw
        else:
            dt = datetime.now(timezone.utc)
        
        memory.retain(
            content=postmortem_text,
            context="incident postmortem",
            timestamp=dt,
        )
        retained_count += 1
        log.info(f"Retained incident {inc['id']} ({inc.get('family', 'general')})")
        
    return IngestResponse(retained=retained_count, skipped_families=exclude_family or [])

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest historical incidents into RunbookMind Hindsight bank")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate Hindsight bank before ingestion")
    parser.add_argument("--exclude-family", nargs="*", default=None, help="Incident families to exclude (e.g. redis_cache, redis)")
    args = parser.parse_args()
    
    if args.reset:
        print("Resetting Hindsight bank...")
        memory.reset_bank()
        print("Bank reset complete.")
    else:
        memory.ensure_bank()
        
    res = ingest(exclude_family=args.exclude_family)
    print(f"Successfully retained {res.retained} incidents (skipped: {res.skipped_families}).")

if __name__ == "__main__":
    main()
