"""FastAPI app: /ingest /analyze /feedback /ask /memories /reset (+ demo helpers)."""
import json
import logging
import warnings

# Suppress noisy async resource cleanup warnings in Windows console
warnings.filterwarnings("ignore", category=ResourceWarning)

from fastapi import FastAPI, HTTPException, Query

from backend import analysis, ingest, memory, metrics
from backend.config import DATA_DIR, settings
from backend.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AskRequest,
    AskResponse,
    FeedbackRequest,
    FeedbackResponse,
    IngestResponse,
    MemoryItem,
    MetricsResponse,
)

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="RunbookMind", version="1.0")


def _upstream_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=f"Upstream service failed after retries: {exc}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "bank_id": settings.bank_id, "hindsight_ui": settings.hindsight_ui_url}


@app.post("/ingest", response_model=IngestResponse)
def ingest_incidents(exclude_family: list[str] | None = Query(None)) -> IngestResponse:
    try:
        return ingest.ingest(exclude_family)
    except Exception as exc:  # noqa: BLE001
        raise _upstream_error(exc) from exc


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return analysis.analyze(req)
    except Exception as exc:  # noqa: BLE001
        raise _upstream_error(exc) from exc


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(req: FeedbackRequest) -> FeedbackResponse:
    try:
        return analysis.submit_feedback(req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown alert_id. Analyze an alert first.") from exc
    except Exception as exc:  # noqa: BLE001
        raise _upstream_error(exc) from exc


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    try:
        return analysis.ask(req.question)
    except Exception as exc:  # noqa: BLE001
        raise _upstream_error(exc) from exc


@app.get("/memories", response_model=list[MemoryItem])
def memories(query: str = "incident postmortem and engineer feedback") -> list[MemoryItem]:
    try:
        return sorted(memory.recall(query, max_tokens=6000), key=lambda m: m.date or "", reverse=True)
    except Exception as exc:  # noqa: BLE001
        raise _upstream_error(exc) from exc


@app.post("/reset")
def reset() -> dict:
    """Clear the demo bank (demo use only)."""
    try:
        memory.reset_bank()
    except Exception as exc:  # noqa: BLE001
        raise _upstream_error(exc) from exc
    metrics.clear()
    analysis.ALERTS.clear()
    return {"reset": True}


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    return metrics.summary()


@app.get("/demo-alerts")
def demo_alerts() -> list[dict]:
    return json.loads((DATA_DIR / "demo_alerts.json").read_text())


@app.get("/graph")
def get_graph() -> dict:
    return memory.get_graph()
