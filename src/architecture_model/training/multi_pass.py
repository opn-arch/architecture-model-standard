"""
MultiPassExtractor: 5-pass hierarchical architecture extraction.

Each pass targets a different architectural aspect using the appropriate
context slice, building the model incrementally. Later passes receive
the partial model from earlier passes to ensure consistency.

Pass 1: Structure    → layers, components (from directory tree)
Pass 2: Boundaries   → actors, interfaces (from API endpoints)
Pass 3: Behavior     → capabilities, behaviors (from tasks/workflows)
Pass 4: Relationships → relationships between all entities
Pass 5: Constraints  → constraints (from configs, decorators)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Relationship,
)
from architecture_model.training.context_builder import ContextSlices
from architecture_model.training.surrogate import _strip_fences


@dataclass
class PassResult:
    """Result from a single extraction pass."""
    pass_name: str
    raw_yaml: str
    entities: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True


# ---------------------------------------------------------------------------
# Pass-specific system prompts
# ---------------------------------------------------------------------------

_PASS_PROMPTS = {
    "structure": """\
You are extracting the STRUCTURAL layer of a software architecture.
From the package structure and entry points below, identify:
- layers: architectural tiers (e.g. web, services, data, infrastructure)
- components: deployable modules/packages within each layer

Output ONLY valid YAML:
layers:
  - id: L<n>
    name: <layer name>
    status: ACTIVE
components:
  - id: C<n>
    name: <component name>
    status: ACTIVE
    layer: L<n>

Output raw YAML only — no markdown fences, no explanation.""",

    "boundaries": """\
You are extracting the BOUNDARY layer of a software architecture.
From the API endpoints and interfaces below, identify:
- actors: external agents that interact with the system (humans, services, systems)
- interfaces: APIs, protocols, data exchanges exposed by the system

Output ONLY valid YAML:
actors:
  - id: A<n>
    name: <actor name>
    status: ACTIVE
    type: human|system|external-service
interfaces:
  - id: I<n>
    name: <interface name>
    status: ACTIVE
    type: rest|grpc|graphql|event|cli

Output raw YAML only — no markdown fences, no explanation.""",

    "behavior": """\
You are extracting the BEHAVIORAL layer of a software architecture.
From the tasks, workflows, and event handlers below, identify:
- capabilities: functional blocks (what the system CAN do)
- behaviors: operational sequences, use cases, workflows (HOW the system does it)

Output ONLY valid YAML:
capabilities:
  - id: CAP<n>
    name: <capability name>
    status: ACTIVE
behaviors:
  - id: B<n>
    name: <behavior name>
    status: ACTIVE

Output raw YAML only — no markdown fences, no explanation.""",

    "relationships": """\
You are extracting RELATIONSHIPS between architecture entities.
Given the entities identified so far and the import/dependency graph, identify relationships.

Valid relationship types: realizes, contains, depends-on, exposes, consumes, traces-to, allocated-to, constrained-by

Output ONLY valid YAML:
relationships:
  - type: <relationship-type>
    from: <source entity id>
    to: <target entity id>

Output raw YAML only — no markdown fences, no explanation.""",

    "constraints": """\
You are extracting architectural CONSTRAINTS.
From the configurations, settings, and decorator patterns below, identify:
- constraints: non-functional requirements, design rules, deployment constraints

Output ONLY valid YAML:
constraints:
  - id: CON<n>
    name: <constraint name>
    status: ACTIVE

Output raw YAML only — no markdown fences, no explanation.""",
}


class MultiPassExtractor:
    """5-pass hierarchical architecture extractor.

    Uses an LLM client (surrogate or oracle) to extract architecture
    incrementally, with each pass focusing on a specific aspect.
    """

    def __init__(
        self,
        client: Any,
        context: ContextSlices,
        project_name: str = "unknown",
    ) -> None:
        self._client = client
        self._context = context
        self._project_name = project_name
        self._pass_results: list[PassResult] = []

    async def extract(self) -> ArchitectureModel:
        """Run all 5 passes and merge into a complete model."""
        # Pass 1: Structure
        await self._pass_structure()
        # Pass 2: Boundaries
        await self._pass_boundaries()
        # Pass 3: Behavior
        await self._pass_behavior()
        # Pass 4: Relationships
        await self._pass_relationships()
        # Pass 5: Constraints
        await self._pass_constraints()

        return self._merge_results()

    async def _pass_structure(self) -> PassResult:
        """Pass 1: Extract layers and components from structure."""
        result = await self._run_pass(
            "structure",
            self._context.structure,
        )
        self._pass_results.append(result)
        return result

    async def _pass_boundaries(self) -> PassResult:
        """Pass 2: Extract actors and interfaces from boundaries."""
        result = await self._run_pass(
            "boundaries",
            self._context.boundaries,
        )
        self._pass_results.append(result)
        return result

    async def _pass_behavior(self) -> PassResult:
        """Pass 3: Extract capabilities and behaviors."""
        result = await self._run_pass(
            "behavior",
            self._context.behavior,
        )
        self._pass_results.append(result)
        return result

    async def _pass_relationships(self) -> PassResult:
        """Pass 4: Extract relationships (receives prior entities)."""
        # Build context with all entities found so far
        prior_entities = self._summarize_prior_entities()
        context = (
            f"# ENTITIES IDENTIFIED SO FAR\n{prior_entities}\n\n"
            f"# DEPENDENCY/IMPORT INFORMATION\n{self._context.relationships}"
        )
        result = await self._run_pass("relationships", context)
        self._pass_results.append(result)
        return result

    async def _pass_constraints(self) -> PassResult:
        """Pass 5: Extract constraints from configs."""
        result = await self._run_pass(
            "constraints",
            self._context.constraints,
        )
        self._pass_results.append(result)
        return result

    async def _run_pass(self, pass_name: str, context_slice: str) -> PassResult:
        """Execute a single extraction pass."""
        system_prompt = _PASS_PROMPTS[pass_name]
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_slice},
        ]

        try:
            response = await self._client._chat(messages)
            content = response.get("message", {}).get("content", "")
            content = _strip_fences(content)

            raw = yaml.safe_load(content)
            if not isinstance(raw, dict):
                return PassResult(pass_name=pass_name, raw_yaml=content, success=False)

            # Extract entities and relationships
            entities = {k: v for k, v in raw.items() if k != "relationships"}
            relationships = raw.get("relationships", [])

            return PassResult(
                pass_name=pass_name,
                raw_yaml=content,
                entities=entities,
                relationships=relationships if isinstance(relationships, list) else [],
            )
        except Exception:
            return PassResult(pass_name=pass_name, raw_yaml="", success=False)

    def _summarize_prior_entities(self) -> str:
        """Build a YAML summary of all entities found in prior passes."""
        combined: dict[str, list] = {}
        for result in self._pass_results:
            if not result.success:
                continue
            for key, value in result.entities.items():
                if isinstance(value, list):
                    combined.setdefault(key, []).extend(value)

        if not combined:
            return "(no entities found yet)"

        try:
            return yaml.dump(combined, default_flow_style=False, sort_keys=False)
        except Exception:
            return str(combined)

    def _merge_results(self) -> ArchitectureModel:
        """Merge all pass results into a single ArchitectureModel."""
        # Combine all entities and relationships into a single dict
        merged: dict[str, Any] = {
            "meta": {
                "schema_version": "1.0",
                "project": self._project_name,
            },
            "entities": {
                "actors": [],
                "capabilities": [],
                "behaviors": [],
                "interfaces": [],
                "constraints": [],
                "layers": [],
                "components": [],
            },
            "relationships": [],
        }

        for result in self._pass_results:
            if not result.success:
                continue

            # Merge entities
            for key, value in result.entities.items():
                if key in merged["entities"] and isinstance(value, list):
                    merged["entities"][key].extend(value)

            # Merge relationships
            if result.relationships:
                merged["relationships"].extend(result.relationships)

        # Parse into ArchitectureModel using existing parser
        try:
            return _parse_raw(merged)
        except Exception:
            # Fallback: return empty model with whatever we got
            return ArchitectureModel(
                meta=ModelMeta(schema_version="1.0", project=self._project_name),
                entities=Entities(),
                relationships=[],
            )
