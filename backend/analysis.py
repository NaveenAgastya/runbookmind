"""Alert analysis, feedback and conversational query orchestration."""
import re
import time
import uuid
from datetime import datetime, timezone

from backend import cache, llm, memory, metrics, prompts
from backend.config import settings
from backend.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AskResponse,
    FeedbackRequest,
    FeedbackResponse,
    MemoryItem,
    Suggestion,
)

INC_ID = re.compile(r"INC-\d{4}")
OUTCOME_TEXT = {"worked": "WORKED", "partial": "PARTIALLY WORKED", "failed": "DID NOT WORK"}

# alert_id -> original request and suggestion, so feedback can be linked to it
ALERTS: dict[str, tuple[AnalyzeRequest, Suggestion]] = {}


def _safe_suggestion(raw: dict, memories: list[MemoryItem], reflection: str, grounded: bool) -> Suggestion:
    """Validate the LLM output and strip any incident ID that was not actually recalled."""
    suggestion = Suggestion(**raw)
    if not grounded:
        suggestion.similar_incidents = []
        suggestion.based_on_team_history = False
        suggestion.confidence = "low"
        return suggestion
    known = set(INC_ID.findall(" ".join(m.text for m in memories) + " " + reflection))
    suggestion.similar_incidents = [s for s in suggestion.similar_incidents if s.id in known]
    suggestion.based_on_team_history = True
    if not suggestion.similar_incidents and suggestion.confidence == "high":
        suggestion.confidence = "medium"
    return suggestion


def _generate(req: AnalyzeRequest) -> tuple[Suggestion, list[MemoryItem]]:
    if not req.use_memory:
        raw = llm.complete_json(prompts.SYSTEM_NO_MEMORY, prompts.alert_block(req))
        return _safe_suggestion(raw, [], "", grounded=False), []

    query = prompts.recall_query(req)
    memories = memory.recall(query)

    if not memories:
        # FR-7: say so plainly, give general guidance, never fabricate incidents.
        raw = llm.complete_json(prompts.SYSTEM_NO_MEMORY, prompts.alert_block(req))
        suggestion = _safe_suggestion(raw, [], "", grounded=False)
        suggestion.confidence_reason = "No relevant team history was found. This is general guidance, not based on team history."
        return suggestion, []

    reflection = ""
    if settings.use_reflect_in_analyze:
        try:
            reflection = memory.reflect(prompts.REFLECT_QUESTION + prompts.alert_block(req))
        except Exception:
            # Reflection is optional reasoning enhancement; memories provide primary grounding
            reflection = ""

    raw = llm.complete_json(prompts.SYSTEM_MEMORY, prompts.memory_prompt(req, memories, reflection))
    return _safe_suggestion(raw, memories, reflection, grounded=True), memories


def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    started = time.perf_counter()
    from_cache = False
    try:
        suggestion, memories = _generate(req)
    except Exception:  # noqa: BLE001 - fall back to cached known-good answer, else surface the error
        cached = cache.lookup(req)
        if cached is None:
            raise
        (suggestion, memories), from_cache = cached, True
    alert_id = f"ALR-{uuid.uuid4().hex[:8]}"
    ALERTS[alert_id] = (req, suggestion)
    return AnalyzeResponse(
        alert_id=alert_id,
        used_memory=req.use_memory,
        suggestion=suggestion,
        memories=memories,
        latency_ms=int((time.perf_counter() - started) * 1000),
        from_cache=from_cache,
    )


def feedback_text(alert_id: str, req: AnalyzeRequest, fb: FeedbackRequest) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    text = (
        f"FEEDBACK on alert {alert_id} at {now} for {req.service} (symptom: {req.title}; {req.log_snippet[:160]}). "
        f"Agent suggested: {fb.action_tried}. Outcome: {OUTCOME_TEXT[fb.outcome]}."
    )
    if fb.minutes_to_resolve is not None:
        text += f" Time to resolve: {fb.minutes_to_resolve} minutes."
    if fb.actual_root_cause:
        text += f" Actual root cause: {fb.actual_root_cause}."
    if fb.actual_fix:
        text += f" Actual fix: {fb.actual_fix}."
    if fb.notes:
        text += f" Engineer notes: {fb.notes}."
    return text


def submit_feedback(fb: FeedbackRequest) -> FeedbackResponse:
    if fb.alert_id not in ALERTS:
        raise KeyError(fb.alert_id)
    req, _ = ALERTS[fb.alert_id]
    memory.retain(feedback_text(fb.alert_id, req, fb), context="engineer feedback")
    metrics.record(fb.alert_id, fb.outcome)
    recallable = False
    for _ in range(4):  # retained memories may take a moment to become recallable
        found = memory.recall(f"FEEDBACK on alert {fb.alert_id}", max_tokens=800)
        if any(fb.alert_id in m.text for m in found):
            recallable = True
            break
        time.sleep(1.5)
    return FeedbackResponse(
        stored=True,
        recallable=recallable,
        message="Feedback stored and recallable." if recallable else "Feedback stored; it may take a few seconds to become recallable.",
    )


def ask(question: str) -> AskResponse:
    sources = memory.recall(question, 1500)
    answer = memory.reflect(question)
    return AskResponse(answer=answer or "No answer found in team history.", sources=sources[:5])
