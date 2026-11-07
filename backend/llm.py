# backend/llm.py
"""Groq LLM wrapper with simple retry logic.
The ``Groq`` client from ``groq`` expects an ``api_key`` and supports ``chat.completions.create``.
We expose a ``call_llm`` that takes a system prompt and user message and returns the content.
"""

import os
import time
from typing import Any, List

import httpx
from groq import Groq
from pydantic import BaseModel

from .config import GROQ_API_KEY

# Initialise client – the ``groq`` library uses the environment variable ``GROQ_API_KEY``
# but we also allow passing explicitly.
client = Groq(api_key=GROQ_API_KEY)


class LLMResponse(BaseModel):
    content: str


def call_llm(system_prompt: str, user_message: str, max_retries: int = 3, backoff: float = 1.5) -> str:
    """Send a chat completion request to Groq and return the assistant's message.

    Parameters
    ----------
    system_prompt: str
        System‑level instruction (LLM_SYSTEM_PROMPT).
    user_message: str
        The actual query (often the reflect output).
    max_retries: int, default 3
        Number of retry attempts on network / 5xx errors.
    backoff: float, default 1.5
        Seconds to wait between retries (exponential).
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model="gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
                max_output_tokens=1024,
            )
            # ``choices`` list always has one element for Groq
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt == max_retries:
                raise
            time.sleep(backoff ** attempt)
    # Should never reach here
    raise RuntimeError("LLM call failed after retries")
