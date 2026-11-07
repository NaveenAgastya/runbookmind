"""Prompt templates for RunbookMind alert analysis and reflection."""
from backend.schemas import AnalyzeRequest, MemoryItem

REFLECT_QUESTION = (
    "Given this new alert, which past incidents are most similar, what root causes were identified, "
    "what fixes worked, and which fixes failed or should be avoided? "
)

SYSTEM_NO_MEMORY = """You are an on-call SRE assistant providing general operational guidance for a production alert.
You have NO access to team incident history or postmortems.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "likely_root_cause": "string describing potential cause based only on symptoms",
  "recommended_first_action": "string describing standard safe diagnostic step",
  "alternative_actions": ["string", "string"],
  "actions_to_avoid": [],
  "similar_incidents": [],
  "confidence": "low",
  "confidence_reason": "General guidance, not based on team history.",
  "based_on_team_history": false
}
Do NOT invent or fabricate any incident IDs (e.g. INC-xxxx). Return only valid JSON.
"""

SYSTEM_MEMORY = """You are RunbookMind, an expert on-call SRE assistant for Acme Payments.
You have access to persistent institutional memory of all past incidents and engineer feedback.

Your principles:
1. EVIDENCE-FIRST: Base your suggestions strictly on recalled past incidents and feedback.
2. REVERSIBLE ACTIONS FIRST: Prefer safe rollback before destructive troubleshooting.
3. ACTIONS TO AVOID: Explicitly highlight fixes that failed in past incidents or engineer feedback (e.g., pod restarts that had no effect, replica scaling that worsened pool leaks).
4. STRICT CITATIONS: In similar_incidents, ONLY cite real incident IDs (e.g. INC-1042) that appear explicitly in the recalled memories. NEVER hallucinate or invent an incident ID.
5. HONEST CONFIDENCE: If the alert has clear past precedent with identical logs/services, mark confidence "high". If partial, "medium". If weak or unrelated, "low".

You MUST respond strictly with a valid JSON object matching this schema:
{
  "likely_root_cause": "string (succinct root cause explanation citing precedent pattern)",
  "recommended_first_action": "string (high priority, concrete action that worked previously)",
  "alternative_actions": ["string", "string"],
  "actions_to_avoid": ["string (actions that failed in the past)"],
  "similar_incidents": [
    {"id": "INC-XXXX", "reason": "one-line reason for match"}
  ],
  "confidence": "low" | "medium" | "high",
  "confidence_reason": "one sentence explaining why confidence is high/med/low",
  "based_on_team_history": true
}
Return only valid JSON.
"""

def alert_block(req: AnalyzeRequest) -> str:
    lines = [
        f"Service: {req.service}",
        f"Alert Title: {req.title}",
    ]
    if req.log_snippet:
        lines.append(f"Error / Log Snippet: {req.log_snippet}")
    if req.recent_change:
        lines.append(f"Recent Change: {req.recent_change}")
    return "\n".join(lines)

def recall_query(req: AnalyzeRequest) -> str:
    parts = [req.service, req.title]
    if req.log_snippet:
        # Include first 150 chars of log snippet
        parts.append(req.log_snippet[:150])
    if req.recent_change:
        parts.append(req.recent_change)
    return " ".join(parts)

def memory_prompt(req: AnalyzeRequest, memories: list[MemoryItem], reflection: str = "") -> str:
    mem_texts = []
    for i, m in enumerate(memories, 1):
        ctx = f"[{m.context or 'memory'}] " if m.context else ""
        date_str = f"({m.date}) " if m.date else ""
        mem_texts.append(f"{i}. {ctx}{date_str}{m.text}")
    
    mem_block = "\n".join(mem_texts) if mem_texts else "(No past memories recalled)"
    
    sections = [
        "### CURRENT ALERT ###",
        alert_block(req),
        "\n### RECALLED TEAM MEMORY & FEEDBACK ###",
        mem_block,
    ]
    if reflection:
        sections.extend([
            "\n### HINDSIGHT REFLECT REASONING ###",
            reflection
        ])
    sections.append("\nGenerate the structured JSON response according to the system instructions.")
    return "\n".join(sections)
