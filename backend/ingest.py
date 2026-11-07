import json, pathlib, datetime
from .hindsight_client import client, BANK_ID

DATA_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "incidents.json"

def load_incidents():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        incidents = json.load(f)

    for inc in incidents:
        # Convert ISO string to datetime if needed
        if isinstance(inc["date"], str):
            inc["date"] = datetime.datetime.fromisoformat(inc["date"])
        # Build a single-paragraph narrative for Hindsight
        narrative = (
            f"{inc['id']} ({inc['date'].date()}, {inc['severity']}): "
            f"{inc['symptoms']} "
            f"Root cause: {inc['root_cause']}. "
            f"Actions tried: {', '.join(inc['actions_tried'])}. "
            f"Resolution: {inc['resolution']}. "
            f"Permanent fix: {inc.get('permanent_fix', '')}."
        )
        client.retain(
            bank_id=BANK_ID,
            content=narrative,
            timestamp=inc['date'].isoformat(),
            context="incident postmortem",
            document_id=inc['id'],
        )
        print(f"Retained {inc['id']}")
    
if __name__ == "__main__":
    load_incidents()
