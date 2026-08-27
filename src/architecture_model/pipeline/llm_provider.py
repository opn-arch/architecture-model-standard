"""LLM provider auto-detection for pipeline reviews.

Supports three pathways:
1. copilot-relay — local SSE server at http://localhost:8400/chat
2. OpenAI — via OPENAI_API_KEY env var
3. Anthropic — via ANTHROPIC_API_KEY env var
"""
from __future__ import annotations

import json
import os
from enum import Enum
from typing import Any, Callable

COPILOT_RELAY_URL = "http://localhost:8400/chat"


class LLMProvider(Enum):
    COPILOT_RELAY = "copilot-relay"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NONE = "none"


def _copilot_relay_available() -> bool:
    """Check if copilot-relay is running."""
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8400/health", method="GET")
        with urllib.request.urlopen(req, timeout=1):
            return True
    except Exception:
        return False


async def _call_copilot_relay(system_prompt: str, user_prompt: str, timeout: int = 180) -> str:
    """Call copilot-relay SSE endpoint and collect full response."""
    try:
        import aiohttp
    except ImportError:
        return ""
    payload = {"content": user_prompt, "system_prompt": system_prompt}
    full_response = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            COPILOT_RELAY_URL, json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            async for line in resp.content:
                text = line.decode("utf-8").strip()
                if text.startswith("data: "):
                    data = json.loads(text[6:])
                    if data.get("type") == "chunk":
                        full_response = data.get("content", "")
                    elif data.get("type") == "done":
                        break
                    elif data.get("type") == "error":
                        break
    return full_response


async def copilot_relay_callback(stage: str, prompt: str, context: dict[str, Any] | None = None) -> str:
    """LLM callback using copilot-relay."""
    system_prompt = (
        "You are an architecture model reviewer. Analyze pipeline stage output and "
        "return structured JSON with corrections and suggestions. "
        "Always respond with valid JSON matching the requested schema."
    )
    return await _call_copilot_relay(system_prompt, prompt)


async def _openai_callback(stage: str, prompt: str, context: dict[str, Any] | None = None) -> str:
    """LLM callback using OpenAI API."""
    try:
        import openai
    except ImportError:
        return ""
    client = openai.AsyncOpenAI()
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an architecture model reviewer. Return structured JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


async def _anthropic_callback(stage: str, prompt: str, context: dict[str, Any] | None = None) -> str:
    """LLM callback using Anthropic API."""
    try:
        import anthropic
    except ImportError:
        return ""
    client = anthropic.AsyncAnthropic()
    resp = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system="You are an architecture model reviewer. Return structured JSON.",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else ""


def detect_provider() -> LLMProvider:
    """Detect the best available LLM provider."""
    if _copilot_relay_available():
        return LLMProvider.COPILOT_RELAY
    if os.getenv("OPENAI_API_KEY"):
        return LLMProvider.OPENAI
    if os.getenv("ANTHROPIC_API_KEY"):
        return LLMProvider.ANTHROPIC
    return LLMProvider.NONE


_CALLBACKS: dict[LLMProvider, Callable] = {
    LLMProvider.COPILOT_RELAY: copilot_relay_callback,
    LLMProvider.OPENAI: _openai_callback,
    LLMProvider.ANTHROPIC: _anthropic_callback,
}


def create_llm_callback() -> Callable | None:
    """Create an LLM callback using the best available provider."""
    provider = detect_provider()
    return _CALLBACKS.get(provider)
