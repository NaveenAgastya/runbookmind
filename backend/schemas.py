"""Pydantic models for the API and the LLM's structured output."""
from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]
Outcome = Literal["worked", "partial", "failed"]


class SimilarIncident(BaseModel):
    id: str
    reason: str


class Suggestion(BaseModel):
    likely_root_cause: str
    recommended_first_action: str
    alternative_actions: list[str] = Field(default_factory=list)
    actions_to_avoid: list[str] = Field(default_factory=list)
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)
    confidence: Confidence = "low"
    confidence_reason: str = ""
    based_on_team_history: bool = False


class AnalyzeRequest(BaseModel):
    service: str
    title: str
    log_snippet: str = ""
    recent_change: str = ""
    use_memory: bool = True


class MemoryItem(BaseModel):
    text: str
    type: str | None = None
    date: str | None = None
    context: str | None = None


class AnalyzeResponse(BaseModel):
    alert_id: str
    used_memory: bool
    suggestion: Suggestion
    memories: list[MemoryItem] = Field(default_factory=list)
    latency_ms: int
    from_cache: bool = False


class FeedbackRequest(BaseModel):
    alert_id: str
    action_tried: str
    outcome: Outcome
    actual_root_cause: str = ""
    actual_fix: str = ""
    notes: str = ""
    minutes_to_resolve: int | None = None


class FeedbackResponse(BaseModel):
    stored: bool
    recallable: bool
    message: str


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    sources: list[MemoryItem] = Field(default_factory=list)


class IngestResponse(BaseModel):
    retained: int
    skipped_families: list[str] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    total: int
    worked: int
    accuracy_pct: float | None
    series: list[float]
