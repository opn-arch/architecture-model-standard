"""Self-reflective prompt evolution for oracle extraction.

Periodically reflects on poor extractions, asks oracle to analyze
failures and suggest prompt improvements. Maintains prompt lineage.
"""

from __future__ import annotations

import yaml
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.training.oracle import Oracle
    from architecture_model.training.oracle_performance import OraclePerformanceStore

# The base prompt that gets evolved
_BASE_EXTRACTION_PROMPT = """\
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


_REFLECTION_PROMPT = """\
You are improving your own architecture extraction instructions.

Here are recent extractions that scored poorly on manifest coverage:

{failures}

For each, the manifest shows these modules/interfaces were missed:
{gaps}

Analyze WHY these patterns were missed. Then suggest specific improvements \
to the extraction system prompt.

Return YAML:
analysis:
  - pattern: "what was missed"
    reason: "why it was missed"
prompt_additions:
  - "new instruction to add"
prompt_removals:
  - "instruction to remove (if misleading)"
"""


class PromptEvolver:
    """Self-reflective prompt evolution for oracle."""

    def __init__(
        self,
        performance_store: "OraclePerformanceStore",
        batch_size: int = 10,
        quality_threshold: float = 0.7,
    ) -> None:
        self._store = performance_store
        self._batch_size = batch_size
        self._quality_threshold = quality_threshold
        self._current_prompt = _BASE_EXTRACTION_PROMPT
        self._version = 1
        self._last_evolved_iteration = 0

    def get_current_prompt(self) -> str:
        """Return the current evolved prompt."""
        return self._current_prompt

    @property
    def version(self) -> int:
        return self._version

    def should_evolve(self, current_iteration: int) -> bool:
        """Check if prompt should evolve (batch trigger or quality drop)."""
        # Quality drop trigger
        avg_coverage = self._store.get_average_coverage()
        if avg_coverage > 0 and avg_coverage < self._quality_threshold:
            return True

        # Batch size trigger
        count = self._store.count_since_iteration(self._last_evolved_iteration)
        return count >= self._batch_size

    async def evolve(self, oracle: "Oracle") -> str:
        """Reflect on failures and evolve the prompt.

        Asks oracle to analyze its own poor extractions and suggest
        prompt improvements. Applies suggestions to create new variant.

        Returns:
            The new evolved prompt.
        """
        poor = self._store.get_poor_extractions(threshold=self._quality_threshold, limit=5)
        if not poor:
            return self._current_prompt

        # Format failures for reflection
        failures = self._format_failures(poor)
        gaps = self._format_gaps(poor)

        reflection = _REFLECTION_PROMPT.format(failures=failures, gaps=gaps)

        # Ask oracle to reflect
        messages = [
            {"role": "system", "content": "You are a prompt engineering expert."},
            {"role": "user", "content": reflection},
        ]
        response = await oracle._completion(messages)
        content = response.choices[0].message.content

        # Parse YAML response
        try:
            suggestions = yaml.safe_load(content)
        except yaml.YAMLError:
            return self._current_prompt

        if not isinstance(suggestions, dict):
            return self._current_prompt

        # Apply suggestions
        new_prompt = self._apply_suggestions(suggestions)
        self._current_prompt = new_prompt
        self._version += 1
        self._last_evolved_iteration = self._store.count()

        return new_prompt

    def _apply_suggestions(self, suggestions: dict) -> str:
        """Apply prompt additions/removals to create new variant."""
        prompt = self._current_prompt

        additions = suggestions.get("prompt_additions", [])
        removals = suggestions.get("prompt_removals", [])

        # Remove lines matching removals
        for removal in removals:
            if isinstance(removal, str) and removal in prompt:
                prompt = prompt.replace(removal, "")

        # Add new instructions before the "Output raw YAML" line
        if additions:
            insertion = "\n\nAdditional instructions:\n"
            for add in additions:
                if isinstance(add, str):
                    insertion += f"- {add}\n"

            # Insert before final instruction
            if "Output raw YAML" in prompt:
                prompt = prompt.replace(
                    "Output raw YAML only",
                    f"{insertion}\nOutput raw YAML only",
                )
            else:
                prompt += insertion

        return prompt

    def _format_failures(self, poor: list) -> str:
        lines = []
        for p in poor:
            lines.append(f"- Repo: {p.repo_url} (coverage: {p.coverage_score:.2f})")
        return "\n".join(lines)

    def _format_gaps(self, poor: list) -> str:
        lines = []
        for p in poor:
            mods = p.uncovered_modules or "[]"
            ifaces = p.uncovered_interfaces or "[]"
            lines.append(f"- {p.repo_url}: missed modules={mods}, missed interfaces={ifaces}")
        return "\n".join(lines)
