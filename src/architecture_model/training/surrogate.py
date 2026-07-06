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

Behaviors have a 'pattern' field:
- sequential (default), event-driven, state-machine, saga, pipeline, parallel
- For state-machine: include 'states' with transitions
- For saga: include 'compensations'

Interfaces may reference a 'schema' (component ID of kind data-model).

And 8 relationship types:
- realizes, contains, depends-on, exposes, consumes, traces-to, allocated-to, constrained-by

Output ONLY valid YAML matching this structure:
meta:
  schema_version: "1.1"
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

Output raw YAML only -- no markdown fences, no explanation."""

_GENERATE_SYSTEM_PROMPT = """\
You are an architecture-to-code compiler. Given a UAM (Universal Architecture Model) \
YAML, generate Python source code that faithfully realizes the described architecture.

Rules:
1. Each component entity becomes ONE Python module (file). Use the component name \
as the filename (e.g., component "parser" → parser.py, component "__init__" → __init__.py).
2. Each module should contain 2-6 classes reflecting the component's responsibilities. \
Include: a primary class implementing core logic, plus supporting classes \
(dataclasses for data models, exceptions for error states, base/abstract classes \
for interfaces the component exposes, enums for type discrimination).
3. Class names should reflect domain terminology from the capabilities and behaviors \
the component realizes/implements — NOT just the component name. For example, \
a "parser" component might contain: Parser, Token, ParseError, Binding.
4. Create methods on each class matching the behaviors it implements and capabilities \
it realizes. A behavior named "Parse Dotenv Stream" on component "parser" → \
Parser.parse_stream(), Parser.read_line(), etc.
5. Add import statements between modules reflecting depends_on and uses relationships. \
Use relative imports (from .module import Class) for intra-package dependencies.
6. Include top-level functions in modules where behaviors don't map cleanly to classes \
(e.g., utility functions, factory functions, module-level API like load_dotenv()).
7. Use type hints on all methods and functions.
8. Do NOT implement method/function bodies — use 'pass' or '...' for all bodies.
9. Include a brief docstring on each class and public function describing its role.

Output format:
- Separate modules with '# component_name.py' comment headers (matching component names exactly)
- Import statements at the top of each module (stdlib first, then relative)
- Output ONLY Python code — no markdown fences, no explanations.

Example structure for a component named "parser" that realizes "File Parsing" capability \
and implements "Parse Stream" behavior:
# parser.py
from typing import Iterator, Optional
from .variables import Variable

class ParseError(Exception):
    \"\"\"Raised when parsing encounters invalid syntax.\"\"\"
    pass

class Token:
    \"\"\"Represents a parsed key-value token.\"\"\"
    key: str
    value: str
    def __init__(self, key: str, value: str) -> None:
        pass

class Parser:
    \"\"\"Core parser for dotenv-format streams.\"\"\"
    def __init__(self, stream: Iterator[str]) -> None:
        pass
    def parse_stream(self) -> list[Token]:
        pass
    def read_line(self, line: str) -> Optional[Token]:
        pass"""


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
