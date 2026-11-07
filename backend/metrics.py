"""Tiny JSON-file log of feedback outcomes for the learning curve (P2)."""
import json
from datetime import datetime, timezone

from backend.config import DATA_DIR
from backend.schemas import MetricsResponse

PATH = DATA_DIR / "metrics.json"
SCORES = {"worked": 1.0, "partial": 0.5, "failed": 0.0}


def _load() -> list[dict]:
    return json.loads(PATH.read_text()) if PATH.exists() else []


def record(alert_id: str, outcome: str) -> None:
    rows = _load()
    rows.append({"alert_id": alert_id, "outcome": outcome, "at": datetime.now(timezone.utc).isoformat()})
    PATH.write_text(json.dumps(rows, indent=2))


def summary() -> MetricsResponse:
    rows = _load()
    series, running = [], 0.0
    for n, row in enumerate(rows, 1):
        running += SCORES[row["outcome"]]
        series.append(round(100 * running / n, 1))
    worked = sum(1 for r in rows if r["outcome"] == "worked")
    return MetricsResponse(total=len(rows), worked=worked, accuracy_pct=series[-1] if series else None, series=series)


def clear() -> None:
    PATH.unlink(missing_ok=True)
