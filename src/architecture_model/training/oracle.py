"""
Oracle: litellm-based frontier model client for ground-truth extraction.

This is the "expensive, high-quality" side of the MPC loop — uses frontier
LLMs (GPT-4o, Claude, etc.) via litellm for provider-agnostic ground truth
architecture extraction and validation.
"""

from __future__ import annotations

from typing import Optional

import yaml

try:
    import litellm

    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import ArchitectureModel


# ---------------------------------------------------------------------------
# System prompts
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

_VALIDATE_SYSTEM_PROMPT = """\
You are an architecture validation engine. Given an extracted architecture \
model (YAML) and the original source code, evaluate whether the extraction \
is correct and complete.

Return your assessment as YAML with this structure:
valid: true/false
issues:
  - description of each issue found
suggestions:
  - improvement suggestions

Output raw YAML only — no markdown fences, no explanation."""


# ---------------------------------------------------------------------------
# Budget Tracker
# ---------------------------------------------------------------------------


class BudgetTracker:
    """Tracks token usage and refuses calls when budget is exhausted."""

    def __init__(self, max_tokens: int) -> None:
        self._max_tokens = max_tokens
        self._used_tokens = 0

    def can_afford(self, estimated_tokens: int) -> bool:
        """Return True if estimated_tokens fit within remaining budget."""
        return estimated_tokens <= self.remaining

    def record_usage(self, tokens_used: int) -> None:
        """Record tokens consumed by a call."""
        self._used_tokens += tokens_used

    @property
    def remaining(self) -> int:
        """Tokens remaining in budget (never negative)."""
        return max(0, self._max_tokens - self._used_tokens)


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------

# Default token estimate for budget checks before making a call
_DEFAULT_ESTIMATED_TOKENS = 1


class Oracle:
    """litellm-based frontier model client for ground-truth extraction."""

    def __init__(
        self,
        model: str = "gpt-4o",
        budget: BudgetTracker | None = None,
    ) -> None:
        self._model = model
        self._budget = budget

    async def extract_model(self, code_context: str) -> Optional[ArchitectureModel]:
        """Extract architecture model from code using a frontier LLM.

        Returns None on parse failure, budget exhaustion, or malformed response.
        """
        # Budget check
        if self._budget is not None and not self._budget.can_afford(_DEFAULT_ESTIMATED_TOKENS):
            return None

        messages = [
            {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": code_context},
        ]

        response = await self._completion(messages)

        # Extract content
        content = response.choices[0].message.content

        # Track token usage
        if self._budget is not None:
            self._budget.record_usage(response.usage.total_tokens)

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

    async def validate_extraction(
        self, model: ArchitectureModel, code: str
    ) -> dict:
        """Validate a surrogate's extraction against the source code.

        Uses the Oracle to review whether the extraction is correct and complete.
        Returns a dict with validation feedback, or empty dict on parse failure.
        """
        # Budget check
        if self._budget is not None and not self._budget.can_afford(_DEFAULT_ESTIMATED_TOKENS):
            return {}

        # Serialize the model to YAML for the prompt
        model_yaml = yaml.dump({
            "meta": {
                "schema_version": model.meta.schema_version,
                "project": model.meta.project,
            },
            "entities": {
                "actors": [{"id": a.id, "name": a.name, "status": a.status.value} for a in model.entities.actors],
                "components": [{"id": c.id, "name": c.name, "status": c.status.value, "layer": c.layer} for c in model.entities.components],
            },
        })

        user_content = (
            f"## Extracted Architecture Model\n\n{model_yaml}\n\n"
            f"## Source Code\n\n{code}"
        )

        messages = [
            {"role": "system", "content": _VALIDATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        response = await self._completion(messages)

        # Extract content
        content = response.choices[0].message.content

        # Track token usage
        if self._budget is not None:
            self._budget.record_usage(response.usage.total_tokens)

        # Parse response as YAML dict
        try:
            result = yaml.safe_load(content)
        except yaml.YAMLError:
            return {}

        if not isinstance(result, dict):
            return {}

        return result

    async def _completion(self, messages: list[dict]) -> object:
        """Call litellm.acompletion with the configured model.

        Raises RuntimeError if litellm is not installed.
        """
        if not HAS_LITELLM:
            raise RuntimeError(
                "litellm is required for Oracle. Install with: pip install litellm"
            )

        return await litellm.acompletion(
            model=self._model,
            messages=messages,
        )
