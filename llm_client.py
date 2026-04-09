"""
llm_client.py
-------------
Shared OpenAI wrapper used by every agent.
"""

import os
import json
from openai import OpenAI

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """Call GPT-4o-mini and return the text response."""
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=2000,
    )
    return response.choices[0].message.content.strip()


def call_llm_json(system_prompt: str, user_prompt: str) -> dict:
    """Call GPT-4o-mini and parse the response as JSON."""
    raw = call_llm(
        system_prompt + "\n\nYou must respond with valid JSON only. No markdown, no explanation.",
        user_prompt,
        temperature=0.3,
    )
    # Strip markdown fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        clean = "\n".join(lines).strip()
    return json.loads(clean)
