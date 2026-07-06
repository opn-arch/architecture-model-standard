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

Components have a 'kind' field:
- service: runtime service, API, daemon
- library: reusable package/module
- data-model: schema, domain object, event payload (include 'fields' list)
- data-store: database, cache, message broker instance
- infrastructure: host, cluster, network, CDN (include 'region' if known)
- framework: framework/platform dependency
- ui: frontend, CLI, dashboard
- pipeline: ETL, CI/CD, batch job

Components MUST have a 'symbols' field listing code types in that module:
  symbols:
    - name: ClassName
      kind: class|dataclass|exception|protocol|enum
      members: [public_method_1, public_method_2]
      supers: [BaseClass]
  functions: [top_level_func_1, top_level_func_2]

Behaviors have a 'pattern' field:
- sequential (default), event-driven, state-machine, saga, pipeline, parallel
- For state-machine: include 'states' with transitions
- For saga: include 'compensations'

Interfaces may reference a 'schema' (component ID of kind data-model).

And 8 relationship types:
- realizes, contains, depends-on, exposes, consumes, traces-to, allocated-to, constrained-by

For 'depends-on' relationships, include 'imports' listing symbols imported:
  - type: depends-on
    from: comp-parser
    to: comp-variables
    imports: [Variable, EnvVariable]

Output ONLY valid YAML matching this structure:
meta:
  schema_version: "1.2"
  project: "<project name>"
  source_language: "python"
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
Each component must have: kind, symbols.
Each relationship must have: type, from, to.

Output raw YAML only -- no markdown fences, no explanation."""

_GENERATE_SYSTEM_PROMPT = """\
You are an architecture-to-code compiler. Given a UAM (Universal Architecture Model) \
YAML with code-level detail, generate Python source code that precisely realizes \
the described architecture.

Rules:
1. Each component entity becomes ONE Python module (file). Use the component name \
as the filename (e.g., component "parser" → parser.py).
2. If the component has a 'symbols' field, use EXACTLY those class/type names:
   - kind=class → class ClassName
   - kind=dataclass → @dataclass class ClassName
   - kind=exception → class ClassName(BaseException)
   - kind=protocol → class ClassName(Protocol)
   - kind=enum → class ClassName(Enum)
   Each symbol's 'members' become methods/fields. Each symbol's 'supers' become base classes.
3. If the component has a 'functions' field, create those exact top-level functions.
4. If no 'symbols' field, generate 2-6 classes reflecting the component's responsibilities \
from capabilities/behaviors it realizes/implements.
5. For each depends-on relationship with an 'imports' field, add:
   from .{target_component_name} import {comma-separated imports}
   If no 'imports' field, infer reasonable imports from the relationship.
6. Use type hints on all methods and functions.
7. Do NOT implement method/function bodies — use 'pass' or '...' for all bodies.
8. Include a brief docstring on each class and public function.

Output format:
- Separate modules with '# component_name.py' comment headers (matching component names exactly)
- Import statements at the top of each module (stdlib first, then relative)
- Output ONLY Python code — no markdown fences, no explanations."""


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
        content = response.get("message", {}).get("content", "")
        # Strip markdown fences (LLMs often ignore "no fences" instructions)
        if "```python" in content:
            content = content.split("```python", 1)[1].split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0]
        return content.strip()

    async def generate_with_prompt(self, system: str, user: str) -> str:
        """Generate code with custom system/user prompts.

        Unlike generate_code() which uses a hardcoded system prompt, this
        allows callers (e.g., TestGuidedGenerator) to supply their own prompts.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        response = await self._chat(messages)
        content = response.get("message", {}).get("content", "")
        # Strip markdown fences
        if "```python" in content:
            content = content.split("```python", 1)[1].split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0]
        return content.strip()

    def confidence(self, model: ArchitectureModel, coverage_score: float | None = None) -> float:
        """Estimate extraction confidence (0-1) using composite signal.

        Combines entity density, relationship density, and optionally
        CoverageScorer.overall for a more meaningful confidence estimate.

        Args:
            model: The extracted architecture model.
            coverage_score: Optional CoverageScorer.overall value (0-1).
        """
        entity_density = min(1.0, model.entity_count / 10)
        # Expect ~1.5 relationships per entity for well-connected model
        expected_rels = model.entity_count * 1.5 + 1
        rel_density = min(1.0, model.relationship_count / expected_rels)

        if coverage_score is not None:
            return 0.4 * entity_density + 0.3 * rel_density + 0.3 * coverage_score
        return 0.6 * entity_density + 0.4 * rel_density

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
