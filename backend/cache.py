"""Known-good cached responses used only if live calls fail (venue network safety net)."""
import json

from backend.config import DATA_DIR
from backend.schemas import AnalyzeRequest, MemoryItem, Suggestion


def lookup(req: AnalyzeRequest) -> tuple[Suggestion, list[MemoryItem]] | None:
    path = DATA_DIR / "cached_responses.json"
    if not path.exists():
        return None
    for row in json.loads(path.read_text()):
        if row["title"].strip().lower() == req.title.strip().lower() and row["use_memory"] == req.use_memory:
            return Suggestion(**row["suggestion"]), [MemoryItem(**m) for m in row["memories"]]
    return None
