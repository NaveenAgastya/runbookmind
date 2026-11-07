"""Groq LLM client wrapper with structured JSON output, retries, and JSON repair."""
import json
import logging
import re
from groq import Groq

from backend.config import settings
from backend.retry import with_retries

log = logging.getLogger("runbookmind.llm")

def _get_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)

def _clean_json_text(text: str) -> str:
    """Strip markdown code fence if present."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    return text

@with_retries(attempts=3, base_delay=1.0)
def complete_json(system_prompt: str, user_prompt: str) -> dict:
    """Call Groq with strict JSON output, retry on error, and repair response."""
    client = _get_client()
    
    # Try calling Groq with JSON object response format
    try:
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1500,
        )
        content = resp.choices[0].message.content or "{}"
    except Exception as e:
        log.warning(f"Groq API call with json_object failed ({e}), retrying without explicit format: {e}")
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        content = resp.choices[0].message.content or "{}"

    cleaned = _clean_json_text(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        log.error(f"Malformed JSON from LLM: {cleaned}")
        raise ValueError(f"Failed to parse LLM JSON: {exc}") from exc
