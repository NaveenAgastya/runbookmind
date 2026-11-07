"""Offline tests: Hindsight and Groq are replaced with fakes."""
import pytest
from fastapi.testclient import TestClient

from backend import analysis, ingest, llm, main, memory, metrics
from backend.schemas import MemoryItem

client = TestClient(main.app)
RECALLED = [MemoryItem(text="INC-1042 (2026-09-14, Sev1): payments-api 5xx after v2.4.1. Rolled back (resolved).", date="2026-09-14", context="incident postmortem")]
LLM_OUT = {
    "likely_root_cause": "pool exhaustion", "recommended_first_action": "roll back",
    "alternative_actions": ["raise pool size"], "actions_to_avoid": ["restart pods"],
    "similar_incidents": [{"id": "INC-1042", "reason": "same signature"}, {"id": "INC-9999", "reason": "fabricated"}],
    "confidence": "high", "confidence_reason": "strong match",
}


@pytest.fixture(autouse=True)
def fakes(monkeypatch, tmp_path):
    retained = []
    monkeypatch.setattr(memory, "recall", lambda q, max_tokens=3000: RECALLED + [MemoryItem(text=t["content"]) for t in retained])
    monkeypatch.setattr(memory, "retain", lambda content, context, timestamp=None: retained.append({"content": content}))
    monkeypatch.setattr(memory, "reflect", lambda q, context=None: "reflection")
    monkeypatch.setattr(llm, "complete_json", lambda system, user: dict(LLM_OUT))
    monkeypatch.setattr(metrics, "PATH", tmp_path / "metrics.json")
    analysis.ALERTS.clear()


ALERT = {"service": "payments-api", "title": "5xx spike", "log_snippet": "HikariPool timeout", "recent_change": "deploy", "use_memory": True}


def test_fabricated_incident_ids_are_removed():
    body = client.post("/analyze", json=ALERT).json()
    assert [i["id"] for i in body["suggestion"]["similar_incidents"]] == ["INC-1042"]
    assert body["suggestion"]["based_on_team_history"] is True


def test_memory_off_has_no_citations():
    body = client.post("/analyze", json={**ALERT, "use_memory": False}).json()
    assert body["suggestion"]["similar_incidents"] == [] and body["memories"] == []


def test_no_recall_gives_labelled_general_guidance(monkeypatch):
    monkeypatch.setattr(memory, "recall", lambda q, max_tokens=3000: [])
    body = client.post("/analyze", json=ALERT).json()
    assert body["suggestion"]["based_on_team_history"] is False
    assert body["suggestion"]["similar_incidents"] == []
    assert body["suggestion"]["confidence"] == "low"


def test_feedback_is_retained_and_tracked():
    alert_id = client.post("/analyze", json=ALERT).json()["alert_id"]
    fb = {"alert_id": alert_id, "action_tried": "roll back", "outcome": "worked", "notes": "pool leak"}
    assert client.post("/feedback", json=fb).json()["recallable"] is True
    assert client.get("/metrics").json()["accuracy_pct"] == 100.0


def test_feedback_unknown_alert_404():
    assert client.post("/feedback", json={"alert_id": "x", "action_tried": "a", "outcome": "failed"}).status_code == 404


def test_dataset_shape():
    incidents = ingest.load_incidents()
    assert 25 <= len(incidents) <= 30 and len({i["id"] for i in incidents}) == len(incidents)
    assert "INC-1042" in ingest.narrative(next(i for i in incidents if i["id"] == "INC-1042"))
