"""
Surrogate: Ollama client wrapper for local LLM extraction and generation.

This is the "cheap, fast" side of the MPC loop — uses a local model
(e.g. CodeLlama) to extract architecture models from code and generate
code from architecture YAML.
"""

from __future__ import annotations

from typing import Any, Optional

import yaml

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import ArchitectureModel
from architecture_model.training.model_config import ModelConfig, get_model_config


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from LLM response."""
    if "```yaml" in text:
        text = text.split("```yaml", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return text.strip()


# ---------------------------------------------------------------------------
# System prompt for architecture extraction
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM_PROMPT = """\
You are an architecture extraction engine. Given source code, extract a \
UAM (Universal Architecture Model) in YAML format.

The model has 7 entity types:
- actors: external agents (human, system, external-service)
- capabilities: functional blocks the system provides
- behaviors: use cases, workflows, operational sequences
- interfaces: APIs, protocols, data exchanges
- constraints: non-functional requirements, design rules
- layers: architectural tiers
- components: deployable units, modules, packages

And 8 relationship types:
- realizes, contains, depends-on, exposes, consumes, traces-to, allocated-to, constrained-by

Output ONLY valid YAML matching this structure:
meta:
  schema_version: "1.0"
  project: "<project name>"
entities:
  actors: [...]
  capabilities: [...]
  behaviors: [...]
  interfaces: [...]
  constraints: [...]
  layers: [...]
  components: [...]
relationships: [...]

Each entity must have: id, name, status (ACTIVE/PLANNED/DORMANT/DEPRECATED).
Each relationship must have: type, from, to.

Output raw YAML only — no markdown fences, no explanation."""

_GENERATE_SYSTEM_PROMPT = """\
You are a code stub generation engine. Given an architecture model YAML, \
generate Python stub code implementing the described architecture. \
Output class definitions with method signatures and brief docstrings. \
Do NOT implement method bodies — use 'pass' or '...' for all bodies. \
Output only Python code — no explanations, no markdown fences."""


class Surrogate:
    """Ollama client wrapper for local LLM architecture extraction."""

    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        host: str = "http://localhost:11434",
        *,
        model_config: Optional[ModelConfig] = None,
    ) -> None:
        if model_config is not None:
            self._config = model_config
        else:
            self._config = get_model_config(model_name)
        self._host = host

    @property
    def model_config(self) -> ModelConfig:
        """Return the active ModelConfig."""
        return self._config

    @property
    def model_name(self) -> str:
        return self._config.ollama_tag

    def swap_model(self, new_model: str | ModelConfig) -> None:
        """Change the active model."""
        if isinstance(new_model, ModelConfig):
            self._config = new_model
        else:
            self._config = get_model_config(new_model)

    async def extract_model(self, code_context: str) -> Optional[ArchitectureModel]:
        """Send code to Ollama, parse YAML response into ArchitectureModel.

        Returns None on parse failure or malformed response.
        """
        messages = [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": code_context},
        ]

        response = await self._chat(messages)

        # Extract text content from response
        content = response.get("message", {}).get("content", "")

        # Strip markdown fences if present
        content = _strip_fences(content)

        # Attempt YAML parse
        try:
            raw = yaml.safe_load(content)
        except yaml.YAMLError:
            return None

        if not isinstance(raw, dict):
            return None

        # Attempt conversion to ArchitectureModel
        try:
            return _parse_raw(raw)
        except Exception:
            return None

    async def generate_code(self, model_slice: str) -> str:
        """Forward pass: architecture YAML → code."""
        messages = [
            {"role": "system", "content": _GENERATE_SYSTEM_PROMPT},
            {"role": "user", "content": model_slice},
        ]

        response = await self._chat(messages)
        return response.get("message", {}).get("content", "")

    def confidence(self, model: ArchitectureModel) -> float:
        """Estimate extraction confidence (0-1) based on entity density.

        Heuristic: min(1.0, total_entities / 10) — caps at 1.0 when 10+ entities.
        """
        return min(1.0, model.entity_count / 10)

    async def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Call Ollama's chat API via aiohttp.

        POST /api/chat with model name and messages.
        Returns the parsed JSON response dict.
        """
        if not HAS_AIOHTTP:
            raise RuntimeError(
                "aiohttp is required for Surrogate. Install with: pip install aiohttp"
            )

        url = f"{self._host}/api/chat"
        payload = {
            "model": self._config.ollama_tag,
            "messages": messages,
            "stream": False,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                return await resp.json()
